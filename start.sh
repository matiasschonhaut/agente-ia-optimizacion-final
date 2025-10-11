#!/bin/bash
set -e

echo "🔹 Iniciando servidor SSH..."
service ssh start

echo "🔹 Iniciando interfaz web Dash..."
python /app/base/web-interface-dash.py
