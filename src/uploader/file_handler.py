import os
import subprocess
import sys
import time
from pathlib import Path
from ..utils import log, config


class FileHandler:

    def __init__(self, serial_handler):
        self.serial = serial_handler

    def upload_py_file(self, file_path):
        if not os.path.exists(file_path):
            log.error(f"File not found: {file_path}")
            return False
        filename = os.path.basename(file_path)
        log.info(f"Uploading: {filename}")
        try:
            cmd = [
                sys.executable, "-m", "ampy.cli",
                "--port", self.serial.port,
                "--baud", str(self.serial.baud_rate),
                "put", file_path, filename
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=config.TIMEOUTS['upload'],
            )
            if result.returncode == 0:
                log.success(f"{filename} uploaded successfully")
                log.info(f"To run in REPL type: import {Path(filename).stem}")
                return True
            else:
                log.warning("ampy failed, trying manual method...")
                return self._upload_manual(file_path)
        except subprocess.TimeoutExpired:
            log.error("Upload timeout")
            return False
        except Exception as e:
            log.warning(f"Error with ampy: {e}")
            return self._upload_manual(file_path)

    def _upload_manual(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            log.info("Sending code...")
            self.serial.write(b'\x03')
            time.sleep(0.1)
            self.serial.write(b'\x04')
            time.sleep(0.5)
            self.serial.reset_buffers()
            for line in code.split('\n'):
                self.serial.write((line + '\n').encode('utf-8'))
                time.sleep(0.01)
            time.sleep(0.5)
            self.serial.write(b'\x04')
            time.sleep(1)
            log.success("Code sent and executed successfully")
            return True
        except Exception as e:
            log.error(f"Manual upload error: {e}")
            return False

    def flash_firmware(self, bin_path):
        if not os.path.exists(bin_path):
            log.error(f".bin file not found: {bin_path}")
            return False
        log.info("Flashing Firmware...")
        print(f"  File: {bin_path}")
        log.info("Please wait (2-3 minutes)...")
        try:
            cmd = [
                sys.executable, "-m", "esptool",
                "--port", self.serial.port,
                "--baud", "460800",
                "--before", "default_reset",
                "--after", "hard_reset",
                "write_flash",
                "-z", "-fm", "dio", "-fs", "detect", "-ff", "40m",
                "0x1000", bin_path
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=config.TIMEOUTS['firmware'],
            )
            if result.returncode == 0:
                log.success("Firmware flashed successfully!")
                log.info("Device booting...")
                time.sleep(2)
                return True
            else:
                log.error(f"Error: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            log.error("Firmware upload timeout")
            return False
        except Exception as e:
            log.error(f"Error: {e}")
            log.info("Note: Install esptool:")
            print("   pip install esptool")
            return False
