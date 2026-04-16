#!/bin/bash
set -e

export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH

echo "🔄 Executando bootstrap do sistema..."
python bootstrap_render.py

echo "🚀 Iniciando aplicação..."
exec gunicorn run:app --bind 0.0.0.0:$PORT