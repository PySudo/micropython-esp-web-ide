import subprocess
import sys
import time
from ..utils import log, config


class DeviceHandler:

    def __init__(self, serial_handler):
        self.serial = serial_handler

    def reset(self):
        log.warning("Full device reset in progress...")
        log.info("Please wait...")
        try:
            cmd = [
                sys.executable, "-m", "esptool",
                "--port", self.serial.port,
                "erase_flash"
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=config.TIMEOUTS['reset'],
            )
            if result.returncode == 0:
                log.success("ESP flash memory wiped successfully")
                log.info("Recommended: Upload new Firmware now")
                return True
            else:
                log.error(f"Error: {result.stderr}")
                return False
        except Exception as e:
            log.error(f"Error: {e}")
            log.info("Note: Install esptool:")
            print("   pip install esptool")
            return False

    def stop_program(self):
        log.info("Stopping program...")
        try:
            self.serial.write(b'\x03')
            time.sleep(0.2)
            log.success("Program stopped")
            return True
        except Exception as e:
            log.error(f"Error: {e}")
            return False

    def soft_reboot(self):
        log.info("Soft rebooting device...")
        try:
            self.serial.write(b'\x04')
            time.sleep(1)
            log.success("Device rebooted")
            return True
        except Exception as e:
            log.error(f"Error: {e}")
            return False
