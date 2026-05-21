#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3 -m pip install -r requirements.txt
python3 web_ide.py --host 127.0.0.1 --port 8765
