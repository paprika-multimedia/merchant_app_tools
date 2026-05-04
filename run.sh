#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python -m pip install -q -r requirements.txt
exec python main.py "$@"
