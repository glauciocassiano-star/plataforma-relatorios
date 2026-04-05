#!/bin/bash
set -e

echo "🔄 Executando bootstrap do sistema..."
python app/bootstrap_render.py

echo "🚀 Iniciando aplicação..."
exec gunicorn run:app