#!/bin/bash
set -e

echo "🔄 Executando bootstrap do sistema..."
python bootstrap_render.py

echo "🚀 Iniciando aplicação..."
exec gunicorn run:app --bind 0.0.0.0:$PORT