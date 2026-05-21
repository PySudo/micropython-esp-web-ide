import serial
import time
from ..utils import log, config


class SerialHandler:

    def __init__(self, port, baud_rate=config.DEFAULT_BAUD_RATE):
        self.port = port
        self.baud_rate = baud_rate
        self.connection = None

    def connect(self):
        try:
            self.connection = serial.Serial(
                self.port,
                self.baud_rate,
                timeout=config.TIMEOUTS['serial']
            )
            time.sleep(0.5)
            log.success(f"Connected to: {self.port}")
            return True
        except serial.SerialException as e:
            log.error(f"Connection error: {e}")
            return False

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None
            log.success("Disconnected")

    def write(self, data):
        if not self.connection:
            return False
        if isinstance(data, str):
            data = data.encode('utf-8')
        try:
            self.connection.write(data)
            return True
        except Exception:
            return False

    def read(self, size=None):
        if not self.connection or not self.connection.in_waiting:
            return b''
        try:
            if size is None:
                return self.connection.read(self.connection.in_waiting)
            return self.connection.read(size)
        except Exception:
            return b''

    def reset_buffers(self):
        if self.connection:
            self.connection.reset_input_buffer()
            self.connection.reset_output_buffer()

    def is_connected(self):
        return self.connection is not None and self.connection.is_open
