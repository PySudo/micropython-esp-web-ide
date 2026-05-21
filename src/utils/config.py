BAUD_RATES = {
    'default': 115200,
    'fast': 460800,
    'slow': 9600
}
DEFAULT_BAUD_RATE = BAUD_RATES['default']
TIMEOUTS = {
    'serial': 1.0,
    'upload': 10,
    'firmware': 300,
    'reset': 60
}
ESP_PATTERNS = ['ESP', 'CH340', 'CH341', 'CP210', 'CP210X', 'FTDI']
REPL_MARKERS = ['>>>', '...']
SYMBOLS = {
    'success': '[OK]',
    'error': '[ERROR]',
    'warning': '[WARN]',
    'info': '[INFO]',
    'upload': '[UPLOAD]',
    'download': '[DOWNLOAD]',
    'monitor': '[MONITOR]',
    'stop': '[STOP]',
    'restart': '[RESTART]',
    'check': '[OK]',
    'repl': '[REPL]',
    'device': '[DEVICE]',
    'file': '[FILE]',
    'arrow': '->'
}
DRIVER_URLS = {
    'ch340': 'https://github.com/MarlinFirmware/Marlin/wiki/Micro-USB-connector',
    'cp210x': 'https://www.silabs.com/products/development-tools/software/usb-to-uart-bridge-vcp-drivers'
}
