from .port_detector import PortDetector
from .serial_handler import SerialHandler
from .file_handler import FileHandler
from .repl_handler import REPLHandler
from .monitor_handler import MonitorHandler
from .device_handler import DeviceHandler
from ..utils import log, config


class ESPMicroPythonManager:

    def __init__(self, port=None, baud_rate=config.DEFAULT_BAUD_RATE):
        self.port = port
        self.baud_rate = baud_rate
        self.serial = None
        self.file_handler = None
        self.repl_handler = None
        self.monitor_handler = None
        self.device_handler = None

    def connect(self):
        if not self.port:
            self.port = PortDetector.auto_detect()
            if not self.port:
                return False
        self.serial = SerialHandler(self.port, self.baud_rate)
        if not self.serial.connect():
            return False
        self.file_handler = FileHandler(self.serial)
        self.repl_handler = REPLHandler(self.serial)
        self.monitor_handler = MonitorHandler(self.serial)
        self.device_handler = DeviceHandler(self.serial)
        return True

    def disconnect(self):
        if self.serial:
            self.serial.disconnect()

    def upload_file(self, file_path):
        if not self.file_handler:
            log.error("Not connected")
            return False
        return self.file_handler.upload_py_file(file_path)

    def flash_firmware(self, bin_path):
        if not self.file_handler:
            log.error("Not connected")
            return False
        return self.file_handler.flash_firmware(bin_path)

    def monitor(self):
        if not self.monitor_handler:
            log.error("Not connected")
            return
        self.monitor_handler.start()

    def repl(self):
        if not self.repl_handler:
            log.error("Not connected")
            return
        self.repl_handler.enter()

    def check_status(self):
        if not self.repl_handler:
            log.error("Not connected")
            return False
        return self.repl_handler.check_status()

    def stop_program(self):
        if not self.device_handler:
            log.error("Not connected")
            return False
        return self.device_handler.stop_program()

    def reset(self):
        if not self.device_handler:
            log.error("Not connected")
            return False
        return self.device_handler.reset()

    def soft_reboot(self):
        if not self.device_handler:
            log.error("Not connected")
            return False
        return self.device_handler.soft_reboot()
