from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from collections import deque
import argparse
import ast
import base64
import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import serial
import serial.tools.list_ports

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"


class BoardError(Exception):
    pass


class BoardSession:

    def __init__(self):
        self.port = None
        self.baud_rate = 115200
        self.ser = None
        self.lock = threading.RLock()
        self.log_lock = threading.Lock()
        self.logs = deque(maxlen=800)
        self.log_seq = 0
        self.monitoring = False
        self.monitor_thread = None
        self.cache_lock = threading.Lock()
        self.cached_files = []
        self.cached_contents = {}
        self.cache_ready = False
        self.cache_message = "Not loaded"

    def add_log(self, text, stream="info"):
        if text is None:
            return
        text = str(text)
        if not text:
            return
        with self.log_lock:
            self.log_seq += 1
            self.logs.append({
                "id": self.log_seq,
                "time": time.strftime("%H:%M:%S"),
                "stream": stream,
                "text": text,
            })

    def get_logs(self, since=0):
        with self.log_lock:
            entries = [entry for entry in self.logs if entry["id"] > since]
            return {"last": self.log_seq, "entries": entries}

    def port_score(self, port):
        haystack = f"{port.device} {port.description} {port.hwid}".upper()
        priority_tokens = [
            ("ESP32", 120),
            ("ESP8266", 120),
            ("ESP", 110),
            ("CP210X", 100),
            ("CP210", 100),
            ("CH340", 95),
            ("CH341", 95),
            ("FTDI", 90),
            ("USB TO UART", 85),
            ("USB UART", 85),
            ("UART BRIDGE", 82),
            ("SILICON LABS", 80),
            ("VID:PID=10C4:EA60", 80),
        ]
        for token, score in priority_tokens:
            if token in haystack:
                return score
        return 0

    def list_ports(self):
        ports = []
        for port in serial.tools.list_ports.comports():
            score = self.port_score(port)
            ports.append({
                "device": port.device,
                "description": port.description,
                "hwid": port.hwid,
                "score": score,
                "detected": score > 0,
            })
        return sorted(ports, key=lambda item: (-item["score"], item["device"]))

    def find_esp_port(self):
        ports = self.list_ports()
        for port in ports:
            if port["detected"]:
                return port["device"]
        return ports[0]["device"] if ports else None

    def connect(self, port=None, baud_rate=None):
        with self.lock:
            if baud_rate:
                self.baud_rate = int(baud_rate)
            if not port:
                port = self.port or self.find_esp_port()
            if not port:
                raise BoardError("No serial port found")
            if self.ser and self.ser.is_open:
                if self.port == port:
                    return self.status()
                self.disconnect()
            try:
                self.ser = serial.Serial(port, self.baud_rate, timeout=0.1)
                self.port = port
                time.sleep(0.4)
                self.add_log(f"Connected to {port} at {self.baud_rate}", "ok")
                return self.status()
            except serial.SerialException as exc:
                self.ser = None
                raise BoardError(str(exc)) from exc

    def disconnect(self):
        with self.lock:
            self.stop_monitor()
            if self.ser:
                try:
                    if self.ser.is_open:
                        self.ser.close()
                finally:
                    self.ser = None
            self.add_log("Disconnected", "warn")
            return self.status()

    def ensure_connected(self):
        if self.ser and self.ser.is_open:
            return
        self.connect(self.port, self.baud_rate)

    def status(self):
        return {
            "connected": bool(self.ser and self.ser.is_open),
            "port": self.port,
            "baud": self.baud_rate,
            "monitoring": self.monitoring,
        }

    def read_available_locked(self, duration=0.4):
        if not self.ser or not self.ser.is_open:
            return ""
        data = bytearray()
        started = time.time()
        while time.time() - started < duration:
            waiting = self.ser.in_waiting
            if waiting:
                data.extend(self.ser.read(waiting))
                time.sleep(0.02)
            elif data:
                break
            else:
                time.sleep(0.02)
        return data.decode("utf-8", errors="replace")

    def read_until_locked(self, marker, timeout=2.0):
        if not self.ser or not self.ser.is_open:
            return b""
        old_timeout = self.ser.timeout
        self.ser.timeout = 0.05
        data = bytearray()
        started = time.time()
        try:
            while time.time() - started < timeout:
                chunk = self.ser.read(1)
                if chunk:
                    data.extend(chunk)
                    if marker in data:
                        break
        finally:
            self.ser.timeout = old_timeout
        return bytes(data)

    def enter_raw_repl_locked(self):
        self.ensure_connected()
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self.ser.write(b"\r\x03\x03")
        time.sleep(0.35)
        self.read_available_locked(0.5)
        self.ser.write(b"\x01")
        response = self.read_until_locked(b">", timeout=2.5)
        if b"raw REPL" in response or response.endswith(b">"):
            return
        raise BoardError("Could not enter raw REPL")

    def exit_raw_repl_locked(self):
        if self.ser and self.ser.is_open:
            self.ser.write(b"\x02")
            time.sleep(0.2)
            self.read_available_locked(0.5)

    def raw_exec(self, code, timeout=5.0, log_output=True):
        with self.lock:
            self.enter_raw_repl_locked()
            try:
                self.ser.write(code.encode("utf-8"))
                self.ser.write(b"\x04")
                ok = self.read_until_locked(b"OK", timeout=2.5)
                if b"OK" not in ok:
                    raise BoardError(ok.decode("utf-8", errors="replace").strip() or "Raw REPL did not accept code")
                stdout = self.read_until_locked(b"\x04", timeout=timeout)
                stderr = self.read_until_locked(b"\x04", timeout=timeout)
                out = stdout.replace(b"\x04", b"").decode("utf-8", errors="replace").strip()
                err = stderr.replace(b"\x04", b"").decode("utf-8", errors="replace").strip()
                if err:
                    self.add_log(err, "error")
                if out and log_output:
                    self.add_log(out, "out")
                return out, err
            finally:
                self.exit_raw_repl_locked()

    def parse_file_list(self, output):
        if not output:
            return None
        text = output.replace("\r\n", "\n").replace("\r", "\n").strip()
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                entries = ast.literal_eval(text[start:end + 1])
                if isinstance(entries, (list, tuple)):
                    return [str(entry) for entry in entries]
            except (SyntaxError, ValueError):
                return None
        return None

    def ampy(self, args, timeout=30):
        self.ensure_connected()
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None
            time.sleep(0.3)
        cmd = [
            sys.executable, "-m", "ampy.cli",
            "--port", self.port,
            "--baud", str(self.baud_rate),
            "--delay", "1",
            *args,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if result.returncode != 0:
            msg = (result.stderr or result.stdout or f"ampy exited with {result.returncode}").strip()
            raise BoardError(msg)
        return result.stdout

    def release_serial_for_tool(self):
        self.ensure_connected()
        self.stop_monitor()
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None
            time.sleep(0.35)

    def run_external_tool(self, cmd, timeout=120):
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        output_lines = []
        started = time.time()
        try:
            while True:
                if timeout and time.time() - started > timeout:
                    proc.kill()
                    raise BoardError("External tool timed out")
                line = proc.stdout.readline() if proc.stdout else ""
                if line:
                    text = line.rstrip()
                    if text:
                        output_lines.append(text)
                        self.add_log(text, "out")
                    continue
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
        finally:
            if proc.stdout:
                proc.stdout.close()
        output = "\n".join(output_lines)
        if proc.returncode != 0:
            raise BoardError(output or f"Command exited with {proc.returncode}")
        return output

    def flash_firmware(self, bin_path, flash_address="0x1000", erase=False):
        if not self.port:
            self.connect()
        if not self.port:
            raise BoardError("No serial port selected")
        if not Path(bin_path).exists():
            raise BoardError("Firmware file was not saved correctly")
        self.add_log("Releasing serial port for esptool...", "info")
        self.release_serial_for_tool()
        try:
            if erase:
                erase_cmd = [
                    sys.executable, "-m", "esptool",
                    "--port", self.port,
                    "--baud", "460800",
                    "erase_flash",
                ]
                self.add_log("Erasing flash...", "warn")
                erase_output = self.run_external_tool(erase_cmd, timeout=120)
            cmd = [
                sys.executable, "-m", "esptool",
                "--port", self.port,
                "--baud", "460800",
                "write_flash",
                flash_address,
                str(bin_path),
            ]
            self.add_log(f"Flashing firmware at {flash_address}...", "cmd")
            output = self.run_external_tool(cmd, timeout=180)
            self.add_log("Firmware flash completed", "ok")
            return {"port": self.port, "address": flash_address, "output": output}
        finally:
            try:
                self.connect(self.port, self.baud_rate)
            except Exception as exc:
                self.add_log(f"Reconnect after flash failed: {exc}", "warn")

    def erase_flash(self):
        if not self.port:
            self.connect()
        if not self.port:
            raise BoardError("No serial port selected")
        self.add_log("Releasing serial port for esptool...", "info")
        self.release_serial_for_tool()
        try:
            cmd = [
                sys.executable, "-m", "esptool",
                "--port", self.port,
                "--baud", "460800",
                "erase_flash",
            ]
            self.add_log("Erasing flash...", "warn")
            output = self.run_external_tool(cmd, timeout=120)
            self.add_log("Flash erase completed", "ok")
            return {"port": self.port, "output": output}
        finally:
            try:
                self.connect(self.port, self.baud_rate)
            except Exception as exc:
                self.add_log(f"Reconnect after erase failed: {exc}", "warn")

    def list_files(self):
        commands = [
            "from os import listdir\nprint(listdir())",
            "from os import listdir\nprint(listdir('/'))",
            "import os\nprint(os.listdir())",
            "import os\nprint(os.listdir('/'))",
            "from uos import listdir\nprint(listdir())",
            "from uos import listdir\nprint(listdir('/'))",
        ]
        last_error = ""
        for command in commands:
            try:
                out, err = self.raw_exec(command, timeout=4.0, log_output=False)
                entries = self.parse_file_list(out)
                if entries is not None:
                    files = sorted(name for name in entries if name and not name.endswith("/"))
                    files = sorted(files)
                    self.set_cached_files(files)
                    return files
                last_error = err or out
            except Exception as exc:
                last_error = str(exc)
        try:
            out = self.ampy(["ls"], timeout=25)
            files = []
            for line in out.splitlines():
                name = line.strip().lstrip("/")
                if name:
                    files.append(name)
            files = sorted(files)
            self.set_cached_files(files)
            return files
        except Exception as exc:
            raise BoardError(f"Could not list files. Raw REPL: {last_error}. ampy: {exc}") from exc

    def normalize_name(self, name):
        clean = (name or "").replace("\\", "/").strip("/")
        if not clean or ".." in clean.split("/"):
            raise BoardError("Invalid file name")
        return clean

    def read_file(self, name):
        name = self.normalize_name(name)
        code = (
            "try:\n"
            "    import ubinascii as binascii\n"
            "except ImportError:\n"
            "    import binascii\n"
            "print('__FILE_BEGIN__')\n"
            f"f = open({name!r}, 'rb')\n"
            "try:\n"
            "    while True:\n"
            "        chunk = f.read(192)\n"
            "        if not chunk:\n"
            "            break\n"
            "        print(binascii.b2a_base64(chunk).decode().strip())\n"
            "finally:\n"
            "    f.close()\n"
            "print('__FILE_END__')\n"
        )
        out, err = self.raw_exec(code, timeout=20.0, log_output=False)
        if err:
            raise BoardError(err)
        match = re.search(r"__FILE_BEGIN__\s*(.*?)\s*__FILE_END__", out, re.S)
        if not match:
            raise BoardError("Could not read file content")
        encoded = "".join(match.group(1).split())
        content = base64.b64decode(encoded or b"").decode("utf-8", errors="replace")
        self.set_cached_content(name, content)
        self.add_log(f"Opened {name}", "ok")
        return {"name": name, "content": content}

    def save_file(self, name, content):
        name = self.normalize_name(name)
        data = content.encode("utf-8")
        out, err = self.raw_exec(f"open({name!r}, 'wb').close()\nprint('READY')", timeout=5.0)
        if err:
            raise BoardError(err)
        written = 0
        for index in range(0, len(data), 192):
            chunk = data[index:index + 192]
            code = (
                f"f = open({name!r}, 'ab')\n"
                "try:\n"
                f"    f.write({chunk!r})\n"
                "finally:\n"
                "    f.close()\n"
            )
            out, err = self.raw_exec(code, timeout=8.0)
            if err:
                raise BoardError(err)
            written += len(chunk)
        out, err = self.raw_exec(
            f"import os\nprint('SAVED', os.stat({name!r})[6])",
            timeout=5.0
        )
        if err:
            raise BoardError(err)
        self.add_log(f"Saved {name} ({len(data)} bytes)", "ok")
        self.set_cached_content(name, content)
        with self.cache_lock:
            if name not in self.cached_files:
                self.cached_files = sorted([*self.cached_files, name])
        return {"name": name, "bytes": len(data), "output": out}

    def delete_file(self, name):
        name = self.normalize_name(name)
        code = (
            "try:\n"
            "    import os\n"
            "except ImportError:\n"
            "    import uos as os\n"
            f"os.remove({name!r})\n"
            "print('DELETED')\n"
        )
        out, err = self.raw_exec(code, timeout=5.0)
        if err:
            raise BoardError(err)
        with self.cache_lock:
            self.cached_files = [file for file in self.cached_files if file != name]
            self.cached_contents.pop(name, None)
        self.add_log(f"Deleted {name}", "warn")
        return {"name": name, "output": out}

    def set_cached_files(self, files):
        with self.cache_lock:
            self.cached_files = list(files)
            self.cache_ready = True
            self.cache_message = f"{len(files)} file(s) cached"

    def set_cached_content(self, name, content):
        with self.cache_lock:
            self.cached_contents[name] = content
            if name not in self.cached_files:
                self.cached_files = sorted([*self.cached_files, name])
            self.cache_ready = True
            self.cache_message = f"{len(self.cached_contents)} file content(s) cached"

    def get_cache(self):
        with self.cache_lock:
            return {
                "ready": self.cache_ready,
                "message": self.cache_message,
                "files": list(self.cached_files),
                "contents": dict(self.cached_contents),
            }

    def prefetch_files(self):
        try:
            files = self.list_files()
            for name in files:
                try:
                    self.read_file(name)
                except Exception as exc:
                    self.add_log(f"Could not prefetch {name}: {exc}", "warn")
            with self.cache_lock:
                self.cache_ready = True
                self.cache_message = f"Prefetched {len(self.cached_contents)} of {len(files)} file(s)"
        except Exception as exc:
            with self.cache_lock:
                self.cache_ready = False
                self.cache_message = str(exc)

    def run_file(self, name):
        name = self.normalize_name(name)
        if not name.lower().endswith(".py"):
            raise BoardError("Only .py files can be run")
        command = f"execfile({name!r})"
        output = self.send_repl_command(command, interrupt=True, read_duration=0.8)
        self.add_log(f"Running {name}", "cmd")
        return {"name": name, "output": output}

    def send_repl_command(self, command, interrupt=True, read_duration=0.8):
        with self.lock:
            self.ensure_connected()
            self.ser.write(b"\x02")
            time.sleep(0.1)
            if interrupt:
                self.ser.write(b"\x03")
                time.sleep(0.2)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.ser.write((command + "\r\n").encode("utf-8"))
            time.sleep(0.15)
            output = self.read_available_locked(read_duration)
            cleaned = self.clean_repl_output(output, command)
            self.add_log(f">>> {command}", "cmd")
            if cleaned:
                self.add_log(cleaned, "out")
            return cleaned

    def clean_repl_output(self, output, command=""):
        if not output:
            return ""
        command = command.strip()
        lines = []
        for line in output.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            stripped = line.strip()
            candidate = stripped
            if candidate.startswith(">>> "):
                candidate = candidate[4:].strip()
            elif candidate.startswith("... "):
                candidate = candidate[4:].strip()
            if not stripped or stripped in (">>>", "..."):
                continue
            if command and candidate == command:
                continue
            lines.append(line)
        return "\n".join(lines).strip()

    def stop_program(self):
        with self.lock:
            self.ensure_connected()
            self.ser.write(b"\x03")
            time.sleep(0.25)
            output = self.read_available_locked(0.6)
            self.add_log("Sent Ctrl+C", "warn")
            if output:
                self.add_log(output, "out")
            return {"output": output}

    def start_monitor(self):
        self.ensure_connected()
        if self.monitoring:
            return self.status()
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        return self.status()

    def stop_monitor(self):
        self.monitoring = False
        return self.status()

    def _monitor_loop(self):
        while self.monitoring:
            try:
                with self.lock:
                    if not self.ser or not self.ser.is_open:
                        self.monitoring = False
                        break
                    waiting = self.ser.in_waiting
                    if waiting:
                        text = self.ser.read(waiting).decode("utf-8", errors="replace")
                        self.add_log(text, "serial")
                time.sleep(0.05)
            except Exception as exc:
                self.add_log(f"Monitor error: {exc}", "error")
                self.monitoring = False
                break
BOARD = BoardSession()


class Handler(BaseHTTPRequestHandler):
    server_version = "MicroPythonWebIDE/1.0"

    def log_message(self, fmt, *args):
        return

    def send_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_error_json(self, message, status=400):
        BOARD.add_log(message, "error")
        self.send_json({"ok": False, "error": message}, status)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def read_multipart_firmware(self):
        import cgi
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            },
        )
        firmware = form["firmware"] if "firmware" in form else None
        if firmware is None or not getattr(firmware, "filename", ""):
            raise BoardError("No firmware .bin file uploaded")
        filename = Path(firmware.filename).name
        if not filename.lower().endswith(".bin"):
            raise BoardError("Please choose a .bin firmware file")
        address = form.getfirst("address", "0x1000").strip() or "0x1000"
        if not re.fullmatch(r"0x[0-9a-fA-F]+|\d+", address):
            raise BoardError("Invalid flash address")
        erase = form.getfirst("erase", "false").lower() in ("1", "true", "yes", "on")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".bin")
        try:
            while True:
                chunk = firmware.file.read(1024 * 128)
                if not chunk:
                    break
                tmp.write(chunk)
            tmp.close()
            return filename, tmp.name, address, erase
        except Exception:
            tmp.close()
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            raise

    def serve_static(self, path):
        if path == "/":
            file_path = WEB_ROOT / "index.html"
        else:
            rel = path.lstrip("/")
            file_path = WEB_ROOT / rel
        try:
            resolved = file_path.resolve()
            if WEB_ROOT.resolve() not in resolved.parents and resolved != WEB_ROOT.resolve():
                self.send_response(403)
                self.end_headers()
                return
            if not resolved.exists() or not resolved.is_file():
                self.send_response(404)
                self.end_headers()
                return
            data = resolved.read_bytes()
            mime = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:
            self.send_error_json(str(exc), 500)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        try:
            if path == "/api/ports":
                ports = BOARD.list_ports()
                detected_port = BOARD.find_esp_port()
                self.send_json({
                    "ok": True,
                    "ports": ports,
                    "detected_port": detected_port,
                    "status": BOARD.status(),
                })
            elif path == "/api/status":
                self.send_json({"ok": True, "status": BOARD.status()})
            elif path == "/api/logs":
                since = int(query.get("since", ["0"])[0])
                self.send_json({"ok": True, **BOARD.get_logs(since)})
            elif path == "/api/cache":
                self.send_json({"ok": True, "cache": BOARD.get_cache()})
            elif path == "/api/files":
                self.send_json({"ok": True, "files": BOARD.list_files()})
            elif path == "/api/file":
                name = query.get("name", [""])[0]
                self.send_json({"ok": True, "file": BOARD.read_file(name)})
            else:
                self.serve_static(path)
        except Exception as exc:
            self.send_error_json(str(exc), 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        body = {} if parsed.path == "/api/firmware/flash" else self.read_json()
        try:
            if parsed.path == "/api/connect":
                status = BOARD.connect(body.get("port"), body.get("baud"))
                self.send_json({"ok": True, "status": status})
            elif parsed.path == "/api/disconnect":
                self.send_json({"ok": True, "status": BOARD.disconnect()})
            elif parsed.path == "/api/file":
                result = BOARD.save_file(body.get("name", ""), body.get("content", ""))
                self.send_json({"ok": True, "file": result})
            elif parsed.path == "/api/delete":
                result = BOARD.delete_file(body.get("name", ""))
                self.send_json({"ok": True, "delete": result})
            elif parsed.path == "/api/run":
                result = BOARD.run_file(body.get("name", ""))
                self.send_json({"ok": True, "run": result})
            elif parsed.path == "/api/terminal":
                output = BOARD.send_repl_command(body.get("command", ""))
                self.send_json({"ok": True, "output": output})
            elif parsed.path == "/api/stop":
                self.send_json({"ok": True, "stop": BOARD.stop_program()})
            elif parsed.path == "/api/monitor/start":
                self.send_json({"ok": True, "status": BOARD.start_monitor()})
            elif parsed.path == "/api/monitor/stop":
                self.send_json({"ok": True, "status": BOARD.stop_monitor()})
            elif parsed.path == "/api/firmware/flash":
                filename, tmp_path, address, erase = self.read_multipart_firmware()
                try:
                    result = BOARD.flash_firmware(tmp_path, address, erase)
                    self.send_json({"ok": True, "firmware": {"name": filename, **result}})
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
            elif parsed.path == "/api/firmware/erase":
                result = BOARD.erase_flash()
                self.send_json({"ok": True, "erase": result})
            else:
                self.send_error_json("Unknown endpoint", 404)
        except Exception as exc:
            self.send_error_json(str(exc), 500)


def main():
    parser = argparse.ArgumentParser(description="ESP MicroPython Web IDE")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not WEB_ROOT.exists():
        raise SystemExit("Missing web assets folder")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"MicroPython Web IDE running at {url}")
    print("Press Ctrl+C to stop")
    threading.Thread(target=BOARD.prefetch_files, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        BOARD.disconnect()
        server.server_close()
if __name__ == "__main__":
    main()
