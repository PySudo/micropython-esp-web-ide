import time
from ..utils import log, config


class MonitorHandler:

    def __init__(self, serial_handler):
        self.serial = serial_handler
        self.monitoring = False

    def start(self):
        self.monitoring = True
        try:
            log.banner("Serial Output Monitor (Press Ctrl+C to exit)")
            print("-" * 60)
            while self.monitoring:
                try:
                    data = self.serial.read()
                    if data:
                        try:
                            text = data.decode('utf-8', errors='replace')
                            print(text, end='', flush=True)
                        except Exception:
                            pass
                    time.sleep(0.01)
                except KeyboardInterrupt:
                    log.info("Exiting monitor")
                    self.monitoring = False
                    break
                except Exception as e:
                    log.error(f"Monitor error: {e}")
                    break
        except Exception as e:
            log.error(f"Error: {e}")
        finally:
            self.monitoring = False

    def stop(self):
        self.monitoring = False
        log.info("Monitor stopped")
