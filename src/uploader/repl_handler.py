import time
from ..utils import log, config


class REPLHandler:

    def __init__(self, serial_handler):
        self.serial = serial_handler

    def enter(self):
        try:
            self.serial.write(b'\x03')
            time.sleep(0.2)
            self.serial.reset_buffers()
            log.banner("REPL Mode (Press Ctrl+C to exit)")
            response = self.serial.read()
            if response:
                print(response.decode('utf-8', errors='replace'), end='')
            while True:
                try:
                    cmd = input()
                    self.serial.write((cmd + '\n').encode('utf-8'))
                    time.sleep(0.1)
                    response = self.serial.read()
                    if response:
                        print(response.decode('utf-8', errors='replace'), end='')
                except KeyboardInterrupt:
                    log.info("Exiting REPL")
                    break
                except EOFError:
                    log.info("Exiting REPL")
                    break
        except Exception as e:
            log.error(f"REPL Error: {e}")

    def check_status(self):
        try:
            self.serial.write(b'\x03')
            time.sleep(0.5)
            response = self.serial.read(100)
            if response:
                text = response.decode('utf-8', errors='replace')
                if any(marker in text for marker in config.REPL_MARKERS):
                    log.success("ESP is working and REPL is accessible")
                    return True
            log.warning("Status unknown - connect to REPL")
            return False
        except Exception as e:
            log.error(f"Status check error: {e}")
            return False
