import sys
from .config import SYMBOLS


class Logger:
    @staticmethod
    def success(message):
        print(f"{SYMBOLS['success']} {message}")

    @staticmethod
    def error(message):
        print(f"{SYMBOLS['error']} {message}", file=sys.stderr)

    @staticmethod
    def warning(message):
        print(f"{SYMBOLS['warning']} {message}")

    @staticmethod
    def info(message):
        print(f"{SYMBOLS['info']} {message}")

    @staticmethod
    def debug(message):
        print(f"[DEBUG] {message}")

    @staticmethod
    def banner(title):
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60 + "\n")


log = Logger()
