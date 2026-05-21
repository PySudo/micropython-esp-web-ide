from src.uploader import ESPMicroPythonManager
from src.utils import log, config


class CLI:

    def __init__(self):
        self.manager = None

    def show_menu(self):
        menu = f"""
{config.SYMBOLS['info']} ESP32/ESP8266 MicroPython Manager
{'=' * 60}
1. Upload .py MicroPython file
2. Upload .bin file (Firmware)
3. Display Serial output
4. Stop running program
5. Check program status
6. Full reset (erase memory)
7. Enter REPL
8. Manual port selection
0. Exit
{'=' * 60}
        """
        print(menu)

    def run(self):
        log.banner("ESP32/ESP8266 MicroPython Manager")
        self.manager = ESPMicroPythonManager()
        if not self.manager.connect():
            log.warning("Auto-connection failed")
            ans = input("Do you want to enter port manually? (y/n): ").lower()
            if ans == 'y':
                port = input("Enter COM port: ").strip()
                self.manager = ESPMicroPythonManager(port)
                if not self.manager.connect():
                    log.error("Connection failed")
                    return
            else:
                log.error("Cannot continue without connection")
                return
        while True:
            self.show_menu()
            choice = input("Choose (0-8): ").strip()
            if choice == '1':
                file_path = input("Enter .py file path: ").strip()
                if file_path:
                    self.manager.upload_file(file_path)
                    ans = input("\nDo you want to display output? (y/n): ").lower()
                    if ans == 'y':
                        self.manager.monitor()
            elif choice == '2':
                file_path = input("Enter .bin file path: ").strip()
                if file_path:
                    self.manager.flash_firmware(file_path)
                    ans = input("\nDo you want to display output? (y/n): ").lower()
                    if ans == 'y':
                        self.manager.monitor()
            elif choice == '3':
                self.manager.monitor()
            elif choice == '4':
                self.manager.stop_program()
            elif choice == '5':
                self.manager.check_status()
            elif choice == '6':
                confirm = input("\nThis will erase all memory. Are you sure? (yes/no): ")
                if confirm.lower() == 'yes':
                    self.manager.reset()
            elif choice == '7':
                self.manager.repl()
            elif choice == '8':
                port = input("Enter COM port (example: COM3): ").strip()
                self.manager.port = port
                if self.manager.connect():
                    log.success("Connection established")
                else:
                    log.error("Connection failed")
            elif choice == '0':
                log.info("Goodbye!")
                self.manager.disconnect()
                break
            else:
                log.error("Invalid choice")


def main():
    try:
        cli = CLI()
        cli.run()
    except KeyboardInterrupt:
        log.info("Program stopped")
    except Exception as e:
        log.error(f"Error: {e}")


if __name__ == "__main__":
    main()
