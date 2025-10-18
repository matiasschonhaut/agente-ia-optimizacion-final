#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent IA para optimización de código con Ollama + knowledge.json
"""

import os
import sys
import json
import logging
import requests
import importlib.util
from datetime import datetime
from typing import Dict, Any, Optional

# ==============================
# Configuración de paths
# ==============================
BASE_PATH = os.environ.get('APP_BASE_PATH', '/app/base')
SOURCE_PATH = os.environ.get('APP_SOURCE_PATH', '/app/source')
KNOWLEDGE_BASE_PATH = os.environ.get('APP_KNOWLEDGE_BASE_PATH', '/app/knowledge_base')
LOGS_PATH = os.environ.get('APP_LOGS_PATH', '/app/logs')
SAVED_CODES_PATH = os.path.join(KNOWLEDGE_BASE_PATH, 'saved_codes')

# ==============================
# Configuración de Ollama
# ==============================
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
MODEL_NAME = os.environ.get('MODEL_NAME', 'codellama:7b')

# Crear directorios
for path in [BASE_PATH, SOURCE_PATH, KNOWLEDGE_BASE_PATH, LOGS_PATH, SAVED_CODES_PATH]:
    os.makedirs(path, exist_ok=True)

if SOURCE_PATH not in sys.path:
    sys.path.insert(0, SOURCE_PATH)

# ==============================
# Logging
# ==============================
logging.basicConfig(
    filename=os.path.join(LOGS_PATH, "agent.log"),
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CodeOptimizationAgent:
    """Agente principal con integración Ollama y knowledge.json"""
    
    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.supported_languages = ['python', 'javascript', 'r']
        self.language_modules = {}
        self.ollama_url = f"{OLLAMA_BASE_URL}/api/generate"
        self.model_name = MODEL_NAME
        
        self._load_language_modules()
        self._load_knowledge_base()
        logger.info(f"Agente iniciado - Sesión: {self.session_id}")
    
    # ==============================
    # Carga de módulos por lenguaje
    # ==============================
    def _load_language_modules(self):
        for language in self.supported_languages:
            module_filename = f"source-{language}-ollama.py"
            module_path = os.path.join(SOURCE_PATH, module_filename)
            try:
                spec = importlib.util.spec_from_file_location(
                    f"source_{language}_ollama", module_path
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self.language_modules[language] = module
                    logger.info(f"Módulo {language} cargado desde {module_filename}")
                else:
                    logger.warning(f"No se pudo crear spec para {module_filename}")
            except Exception as e:
                logger.warning(f"No se pudo cargar módulo {language}: {e}")

    # ==============================
    # Carga de base de conocimiento
    # ==============================
    def _load_knowledge_base(self):
        """Carga ejemplos desde knowledge.json si existe"""
        self.knowledge_base = []
        knowledge_file = os.path.join(KNOWLEDGE_BASE_PATH, "knowledge.json")
        try:
            if os.path.exists(knowledge_file):
                with open(knowledge_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "examples" in data:
                        self.knowledge_base = data["examples"]
                    elif isinstance(data, list):
                        self.knowledge_base = data
                    logger.info(f"Cargados {len(self.knowledge_base)} ejemplos desde knowledge.json")
            else:
                logger.warning("Archivo knowledge.json no encontrado")
        except Exception as e:
            logger.error(f"Error cargando knowledge.json: {e}")

    # ==============================
    # Comunicación con Ollama
    # ==============================
    def query_ollama(self, prompt: str) -> str:
        try:
            payload = {"model": self.model_name, "prompt": prompt, "stream": False}
            response = requests.post(self.ollama_url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json().get('response', '')
        except Exception as e:
            logger.error(f"Error consultando Ollama: {e}")
        return ""

    # ==============================
    # Análisis de código
    # ==============================
    def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        if language not in self.supported_languages:
            return {"status": "error", "message": f"Lenguaje {language} no soportado"}
        
        if language in self.language_modules:
            try:
                analyzer = getattr(self.language_modules[language], 'analyze', None)
                if analyzer:
                    results = analyzer(code)
                    if results.get("syntax_valid", False):
                        prompt = f"Analyze this {language} code for issues:\n\n{code[:500]}"
                        ai_suggestions = self.query_ollama(prompt)
                        if ai_suggestions:
                            results["ai_suggestions"] = ai_suggestions[:500]
                    return {"status": "success", "language": language, "analysis": results}
            except Exception as e:
                logger.error(f"Error en análisis: {e}")
                return {"status": "error", "message": str(e)}
        
        return {"status": "error", "message": "Módulo no disponible"}

    # ==============================
    # Optimización de código
    # ==============================
    def optimize_code(self, code: str, language: str) -> Dict[str, Any]:
        if language not in self.supported_languages:
            return {"status": "error", "message": f"Lenguaje {language} no soportado"}
        
        analysis_result = self.analyze_code(code, language)
        
        if analysis_result["status"] == "success" and language in self.language_modules:
            try:
                optimizer = getattr(self.language_modules[language], 'optimize', None)
                if optimizer:
                    analysis_data = analysis_result.get("analysis", {})
                    optimized_result = optimizer(code, {"analysis": analysis_data})
                    
                    # Integrar knowledge.json
                    if hasattr(self, "knowledge_base") and self.knowledge_base:
                        for ex in self.knowledge_base:
                            if ex["input"].strip() in code:
                                optimized_result["code"] = ex["optimized"]
                                optimized_result.setdefault("improvements", []).append(
                                    "Optimización aplicada desde knowledge.json"
                                )
                                logger.info("Optimización obtenida desde knowledge.json")
                                break
                    
                    return {
                        "status": "success",
                        "language": language,
                        "optimized_code": optimized_result.get("code", code),
                        "suggestions": optimized_result.get("suggestions", []),
                        "improvements": optimized_result.get("improvements", [])
                    }
            except Exception as e:
                logger.error(f"Error en optimización: {e}")
                return {"status": "error", "message": str(e)}
        
        return {"status": "error", "message": "No se pudo optimizar"}
