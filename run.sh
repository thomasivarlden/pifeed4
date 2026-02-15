#!/bin/sh
cd "$(dirname "$0")"
. .venv/bin/activate
exec python main.py "$@"
