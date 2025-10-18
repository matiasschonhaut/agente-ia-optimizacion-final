#!/bin/bash
set -e

echo "=== Iniciando Ollama ==="
ollama serve &
sleep 10

echo "Verificando estado de Ollama..."
curl -s http://localhost:11434/api/tags || echo "Ollama aún no responde"

echo "=== Cargando modelo ${MODEL_NAME} ==="
ollama pull ${MODEL_NAME} || echo "No se pudo descargar el modelo, asegúrate de que el nombre sea correcto"

echo "=== Iniciando aplicación Dash ==="
python3 /app/base/web-interface-dash.py
