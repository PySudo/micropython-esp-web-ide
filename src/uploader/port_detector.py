import serial
import serial.tools.list_ports
from ..utils import log, config


class PortDetector:
    @staticmethod
    def find_esp_ports():
        ports = serial.tools.list_ports.comports()
        esp_ports = []
        for port in ports:
            if any(pattern in port.description.upper() for pattern in config.ESP_PATTERNS):
                esp_ports.append((port.device, port.description))
        return esp_ports

    @staticmethod
    def auto_detect():
        esp_ports = PortDetector.find_esp_ports()
        if not esp_ports:
            log.error("No ESP32/ESP8266 found connected!")
            log.info(f"Install USB drivers:")
            print(f"   - CH340: {config.DRIVER_URLS['ch340']}")
            print(f"   - CP210X: {config.DRIVER_URLS['cp210x']}")
            return None
        if len(esp_ports) == 1:
            port = esp_ports[0][0]
            log.success(f"Port found: {port} ({esp_ports[0][1]})")
            return port
        print(f"\n{config.SYMBOLS['device']} Multiple ports found:")
        for i, (port, desc) in enumerate(esp_ports, 1):
            print(f"  {i}. {port} - {desc}")
        try:
            choice = input("\nSelect desired port (1-n): ")
            idx = int(choice) - 1
            if 0 <= idx < len(esp_ports):
                return esp_ports[idx][0]
        except (ValueError, IndexError):
            pass
        log.error("Invalid selection")
        return None

    @staticmethod
    def validate(port):
        if not port:
            return False
        try:
            ports = [p.device for p in serial.tools.list_ports.comports()]
            return port in ports
        except Exception:
            return False
