#!/bin/bash
# Script de inicio para el contenedor

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=================================================="
echo "Iniciando servicios del Agente IA"
echo "=================================================="

# Iniciar SSH
echo -e "\n${YELLOW}Iniciando servicio SSH...${NC}"
service ssh start
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ SSH iniciado en puerto 22${NC}"
else
    echo -e "${RED}✗ Error iniciando SSH${NC}"
fi

# Verificar GPU
echo -e "\n${YELLOW}Verificando disponibilidad de GPU...${NC}"
/app/check_gpu.sh

# Iniciar Ollama con configuración para escuchar en todas las interfaces
echo -e "\n${YELLOW}Iniciando servicio Ollama...${NC}"
export OLLAMA_HOST=0.0.0.0
ollama serve &
OLLAMA_PID=$!

# Función para verificar si Ollama está listo
wait_for_ollama() {
    local max_attempts=30
    local attempt=1
    
    echo "Esperando a que Ollama esté listo..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://0.0.0.0:11434/api/tags >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Ollama está listo (intento $attempt)${NC}"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "\n${RED}✗ Ollama no respondió después de $max_attempts intentos${NC}"
    return 1
}

# Esperar a que Ollama esté completamente iniciado
if wait_for_ollama; then
    # Verificar modelos disponibles
    echo -e "\n${YELLOW}Verificando modelos disponibles...${NC}"
    available_models=$(ollama list 2>/dev/null | grep -v "NAME" | awk '{print $1}')
    
    if [ -z "$available_models" ]; then
        echo "No hay modelos instalados"
    else
        echo "Modelos disponibles:"
        echo "$available_models"
    fi
    
    # Descargar modelo si no existe
    echo -e "\n${YELLOW}Verificando modelo ${MODEL_NAME}...${NC}"
    if ollama list 2>/dev/null | grep -q "^${MODEL_NAME}"; then
        echo -e "${GREEN}✓ Modelo ${MODEL_NAME} ya está instalado${NC}"
    else
        echo "Descargando modelo ${MODEL_NAME}..."
        echo "Esto puede tomar varios minutos dependiendo de la conexión..."
        
        if ollama pull ${MODEL_NAME}; then
            echo -e "${GREEN}✓ Modelo ${MODEL_NAME} descargado exitosamente${NC}"
        else
            echo -e "${RED}✗ Error descargando modelo ${MODEL_NAME}${NC}"
            echo "Puede intentar descargarlo manualmente con: ollama pull ${MODEL_NAME}"
        fi
    fi
    
    # Test rápido del modelo
    echo -e "\n${YELLOW}Probando modelo...${NC}"
    if echo "Hello" | ollama run ${MODEL_NAME} --verbose 2>/dev/null | head -1 >/dev/null; then
        echo -e "${GREEN}✓ Modelo ${MODEL_NAME} funcionando correctamente${NC}"
    else
        echo -e "${YELLOW}⚠ No se pudo verificar el modelo${NC}"
    fi
else
    echo -e "${RED}✗ No se pudo iniciar Ollama correctamente${NC}"
fi

# Mostrar versiones instaladas
echo -e "\n${YELLOW}=== Versiones Instaladas ===${NC}"
echo "Python: $(python --version 2>&1)"
echo "Node.js: $(node --version 2>&1)"
echo "npm: $(npm --version 2>&1)"
echo "R: $(R --version 2>&1 | head -n1)"

# Verificar herramientas de JavaScript
if command -v eslint >/dev/null 2>&1; then
    echo "ESLint: $(eslint --version 2>&1)"
else
    echo "ESLint: no disponible globalmente"
fi

if command -v prettier >/dev/null 2>&1; then
    echo "Prettier: $(prettier --version 2>&1)"
else
    echo "Prettier: no disponible globalmente"
fi

# Verificar herramientas de Python
echo -e "\n${YELLOW}=== Herramientas de Python ===${NC}"
for tool in pylint black isort flake8; do
    if command -v $tool >/dev/null 2>&1; then
        echo "$tool: $($tool --version 2>&1 | head -n1)"
    else
        echo "$tool: no instalado"
    fi
done

# Crear directorios de logs si no existen
mkdir -p /app/logs /app/knowledge_base/saved_codes

# Iniciar aplicación principal
echo -e "\n${YELLOW}Iniciando aplicación web Dash...${NC}"
echo "La aplicación estará disponible en http://localhost:8050"
echo ""

# Configurar variables de entorno para la aplicación
export OLLAMA_BASE_URL=http://0.0.0.0:11434
export PYTHONPATH=/app/base:/app/source:$PYTHONPATH

# Cambiar al directorio de la aplicación
cd /app/base

# Verificar que los archivos necesarios existen
if [ ! -f "web-interface-dash.py" ]; then
    echo -e "${RED}✗ Error: web-interface-dash.py no encontrado${NC}"
    echo "Archivos en /app/base:"
    ls -la /app/base/
    exit 1
fi

if [ ! -f "agent-ollama.py" ]; then
    echo -e "${RED}✗ Error: agent-ollama.py no encontrado${NC}"
    exit 1
fi

# Verificar archivos source
echo -e "\n${YELLOW}Verificando módulos source...${NC}"
for module in source-python-ollama.py source-javascript-ollama.py source-r-ollama.py; do
    if [ -f "/app/source/$module" ]; then
        echo -e "${GREEN}✓ $module presente${NC}"
    else
        echo -e "${RED}✗ $module faltante${NC}"
    fi
done

# Iniciar la aplicación
echo -e "\n${YELLOW}Iniciando servidor Dash...${NC}"
echo "Logs disponibles en: /app/logs/dash.log"
echo ""

# Ejecutar la aplicación principal
exec python web-interface-dash.py