# === Imagen base ===
FROM python:3.10

# === Variables de entorno ===
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    APP_BASE_PATH=/app/base \
    APP_SOURCE_PATH=/app/source \
    APP_KNOWLEDGE_BASE_PATH=/app/knowledge_base \
    APP_LOGS_PATH=/app/logs \
    OLLAMA_BASE_URL=http://localhost:11434 \
    MODEL_NAME=codellama:7b \
    OLLAMA_HOST=0.0.0.0 \
    NODE_VERSION=20.x


# === Dependencias del sistema ===
RUN apt-get update && apt-get install -y \
    curl wget gnupg lsb-release apt-transport-https ca-certificates \
    openssh-server vim nano git build-essential gcc g++ make cmake \
    procps net-tools lsof htop pciutils \
    libcurl4-openssl-dev libssl-dev libxml2-dev \
    libfontconfig1-dev libharfbuzz-dev libfribidi-dev \
    libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

# === Instalar Node.js (v20.x LTS) ===
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION} | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

# === Herramientas Node.js globales ===
RUN npm install -g \
    eslint prettier eslint-config-airbnb-base eslint-plugin-import \
    eslint-config-prettier eslint-plugin-prettier typescript ts-node nodemon pm2

# === Instalar Ollama (no falla si no existe GPU) ===
RUN curl -fsSL https://ollama.com/install.sh | sh || echo "⚠️ Ollama no se pudo instalar, continuando sin él"

# === Configurar SSH ===
RUN mkdir -p /var/run/sshd \
    && echo 'root:opti2025' | chpasswd \
    && sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# === Crear estructura de carpetas ===
RUN mkdir -p /app/base /app/source /app/knowledge_base/saved_codes /app/logs \
    && mkdir -p /root/.ollama/models /app/node_modules

# === Instalar librerías Python ===
RUN pip install --no-cache-dir \
    dash==2.14.1 dash-bootstrap-components==1.5.0 plotly==5.18.0 \
    pylint==3.0.3 black==23.12.1 isort==5.13.2 mypy==1.8.0 flake8==7.0.0 autopep8==2.0.4 \
    requests==2.31.0 pandas==2.1.4 numpy==1.26.2 scipy==1.11.4 scikit-learn==1.3.2 \
    python-dotenv==1.0.0 psutil==5.9.6 torch tensorflow-cpu

# === Crear configuración ESLint / Prettier ===
RUN echo '{\n\
  "env": {"browser": true, "es2021": true, "node": true},\n\
  "extends": ["airbnb-base", "prettier"],\n\
  "plugins": ["prettier"],\n\
  "parserOptions": {"ecmaVersion": "latest", "sourceType": "module"},\n\
  "rules": {"prettier/prettier": "error"}\n\
}' > /app/.eslintrc.json

RUN echo '{\n\
  "semi": true,\n\
  "trailingComma": "es5",\n\
  "singleQuote": true,\n\
  "printWidth": 80,\n\
  "tabWidth": 2\n\
}' > /app/.prettierrc.json

# === Script de diagnóstico GPU (no requerido) ===
RUN echo '#!/bin/bash\n\
echo "=== Sistema Operativo ==="\n\
cat /etc/os-release\n\
echo "\n=== GPU Info ==="\n\
if command -v nvidia-smi &> /dev/null; then nvidia-smi; else echo "Sin GPU NVIDIA"; fi\n\
' > /app/check_gpu.sh && chmod +x /app/check_gpu.sh

# === Copiar archivos de la aplicación ===
WORKDIR /app
COPY web-interface-dash.py /app/base/
COPY agent-ollama.py /app/base/
COPY source-python-ollama.py /app/source/
COPY source-javascript-ollama.py /app/source/
COPY source-r-ollama.py /app/source/
COPY start.sh /app/start.sh

RUN chmod +x /app/start.sh

# === Exponer puertos ===
EXPOSE 22 8050 11434

# === Volúmenes persistentes ===


# === Healthcheck ===
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8050/ || exit 1

# === Comando de inicio ===
CMD ["/app/start.sh"]
