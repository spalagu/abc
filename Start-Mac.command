#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
trap 'echo; echo "启动失败。请保留上面的报错。按回车退出。"; read -r' ERR
if [ "$(uname -s)" != Darwin ]; then echo '真实 Host 需要 macOS。'; exit 1; fi
if ! command -v python3 >/dev/null; then echo '请安装 Python 3.11+，或使用 Releases 中打包好的应用。'; exit 1; fi
python3 -c 'import sys; assert sys.version_info >= (3,11), "需要 Python 3.11+"'
if [ ! -x .venv/bin/python3 ]; then python3 -m venv .venv; fi
.venv/bin/python3 -m pip install -r requirements.txt
exec .venv/bin/python3 -m continuity --gui
