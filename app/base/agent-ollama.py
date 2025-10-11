#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent IA para optimización de código con Ollama
"""

import os
import sys
import json
import logging
import requests
import importlib.util
from datetime import datetime
from typing import Dict, Any, Optional

# Configuración de paths
BASE_PATH = os.environ.get('APP_BASE_PATH', '/app/base')
SOURCE_PATH = os.environ.get('APP_SOURCE_PATH', '/app/source')
KNOWLEDGE_BASE_PATH = os.environ.get('APP_KNOWLEDGE_BASE_PATH', '/app/knowledge_base')
LOGS_PATH = os.environ.get('APP_LOGS_PATH', '/app/logs')
SAVED_CODES_PATH = os.path.join(KNOWLEDGE_BASE_PATH, 'saved_codes')

# Configuración de Ollama
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
MODEL_NAME = os.environ.get('MODEL_NAME', 'codellama:7b')

# Crear directorios
for path in [BASE_PATH, SOURCE_PATH, KNOWLEDGE_BASE_PATH, LOGS_PATH, SAVED_CODES_PATH]:
    os.makedirs(path, exist_ok=True)

if SOURCE_PATH not in sys.path:
    sys.path.insert(0, SOURCE_PATH)

# Logging
logging.basicConfig(
    filename=os.path.join(LOGS_PATH, "agent.log"),
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CodeOptimizationAgent:
    """Agente principal con integración Ollama"""
    
    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.supported_languages = ['python', 'javascript', 'r']
        self.language_modules = {}
        self.ollama_url = f"{OLLAMA_BASE_URL}/api/generate"
        self.model_name = MODEL_NAME
        
        self._load_language_modules()
        logger.info(f"Agente iniciado - Sesión: {self.session_id}")
    
    def _load_language_modules(self):
        """Carga módulos de lenguaje"""
        for language in self.supported_languages:
            # Usar nombres con guiones
            module_filename = f"source-{language}-ollama.py"
            module_path = os.path.join(SOURCE_PATH, module_filename)
            
            try:
                # Cargar módulo dinámicamente desde archivo
                spec = importlib.util.spec_from_file_location(
                    f"source_{language}_ollama", 
                    module_path
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
    
    def query_ollama(self, prompt: str) -> str:
        """Consulta a Ollama"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(self.ollama_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json().get('response', '')
                
        except Exception as e:
            logger.error(f"Error consultando Ollama: {e}")
        
        return ""
    
    def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """Analiza código"""
        if language not in self.supported_languages:
            return {"status": "error", "message": f"Lenguaje {language} no soportado"}
        
        # Análisis con módulo específico
        if language in self.language_modules:
            try:
                analyzer = getattr(self.language_modules[language], 'analyze', None)
                if analyzer:
                    # El módulo retorna directamente los results
                    results = analyzer(code)
                    
                    # Enriquecer con Ollama si la sintaxis es válida
                    if results.get("syntax_valid", False):
                        prompt = f"Analyze this {language} code for issues:\n\n{code[:500]}"
                        ai_suggestions = self.query_ollama(prompt)
                        if ai_suggestions:
                            results["ai_suggestions"] = ai_suggestions[:500]
                    
                    # Retornar con estructura consistente
                    return {
                        "status": "success",
                        "language": language,
                        "analysis": results  # results contiene: syntax_valid, metrics, issues, patterns
                    }
            except Exception as e:
                logger.error(f"Error en análisis: {e}")
                return {"status": "error", "message": str(e)}
        
        return {"status": "error", "message": "Módulo no disponible"}
    
    def optimize_code(self, code: str, language: str) -> Dict[str, Any]:
        """Optimiza código"""
        if language not in self.supported_languages:
            return {"status": "error", "message": f"Lenguaje {language} no soportado"}
        
        # Análisis previo
        analysis_result = self.analyze_code(code, language)
        
        if analysis_result["status"] == "success" and language in self.language_modules:
            try:
                optimizer = getattr(self.language_modules[language], 'optimize', None)
                if optimizer:
                    # Pasar solo el contenido de analysis, no todo el resultado
                    analysis_data = analysis_result.get("analysis", {})
                    
                    # El módulo optimize espera: code y analysis (que contiene syntax_valid, metrics, issues, patterns)
                    optimized_result = optimizer(code, {"analysis": analysis_data})
                    
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