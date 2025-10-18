#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de análisis y optimización para Python
"""

import ast
import subprocess
import tempfile
import os
import json
import re
from typing import Dict, List, Any
import logging
import requests

# Configuración de logging consistente con el proyecto
logger = logging.getLogger(__name__)

# Verificar herramientas disponibles
TOOLS_AVAILABLE = {
    'pylint': False,
    'black': False,
    'isort': False,
    'flake8': False,
    'autopep8': False,
    'mypy': False
}

def check_tools():
    """Verifica disponibilidad de herramientas"""
    for tool in TOOLS_AVAILABLE:
        try:
            result = subprocess.run([tool, '--version'], capture_output=True, check=True, text=True)
            TOOLS_AVAILABLE[tool] = True
            logger.info(f"{tool} disponible: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            logger.debug(f"{tool} no disponible")
        except Exception as e:
            logger.error(f"Error verificando {tool}: {e}")

check_tools()


def analyze(code: str) -> Dict[str, Any]:
    """Analiza código Python"""
    results = {
        "syntax_valid": False,
        "metrics": {},
        "issues": [],
        "patterns": []
    }
    
    try:
        ast.parse(code)
        results["syntax_valid"] = True
        
        lines = code.split('\n')
        results["metrics"] = {
            "total_lines": len(lines),
            "code_lines": sum(1 for l in lines if l.strip() and not l.strip().startswith('#')),
            "comment_lines": sum(1 for l in lines if l.strip().startswith('#')),
            "function_count": len(re.findall(r'def\s+\w+\s*\(', code)),
            "class_count": len(re.findall(r'class\s+\w+\s*[\(:]', code))
        }
        
        results["patterns"] = detect_patterns(code)
        
    except SyntaxError as e:
        results["issues"].append({
            "type": "syntax_error",
            "line": e.lineno,
            "message": str(e),
            "severity": "error"
        })
    except Exception as e:
        logger.error(f"Error en análisis Python: {e}", exc_info=True)
    
    return results


def optimize(code: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Optimiza código Python con heurísticas y conocimiento"""
    result = {
        "code": code,
        "suggestions": [],
        "improvements": []
    }
    
    try:
        analysis_data = analysis.get("analysis", {})
        if not analysis_data.get("syntax_valid", False):
            result["suggestions"].append("Corrija los errores de sintaxis antes de optimizar")
            return result
        
        # === Integración con base de conocimiento ===
        knowledge_path = "/app/knowledge_base/knowledge.json"
        if os.path.exists(knowledge_path):
            try:
                with open(knowledge_path, "r", encoding="utf-8") as f:
                    knowledge_data = json.load(f)

                examples = [
                    ex for ex in knowledge_data
                    if ex.get("language") == "python" and "optimized_code" in ex
                ]
                if examples:
                    context_examples = "\n\n".join(
                        f"Original:\n{ex['code']}\nOptimized:\n{ex['optimized_code']}"
                        for ex in examples[:3]
                    )

                    prompt = (
                        f"You are a Python code optimization assistant. "
                        f"Use the following examples as guidance:\n\n{context_examples}\n\n"
                        f"Now, optimize this Python code by improving style, performance, and readability:\n{code}\n\n"
                        f"Return only the optimized code."
                    )

                    ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
                    model_name = os.environ.get("MODEL_NAME", "codellama:7b")
                    payload = {"model": model_name, "prompt": prompt, "stream": False}
                    response = requests.post(f"{ollama_url}/api/generate", json=payload, timeout=60)

                    if response.status_code == 200:
                        optimized_output = response.json().get("response", "").strip()
                        if optimized_output and optimized_output != code:
                            result["code"] = optimized_output
                            result["improvements"].append({
                                "type": "ai_optimization",
                                "source": "knowledge_base"
                            })
                            logger.info("Optimización AI aplicada con ejemplos del knowledge.json")

            except Exception as e:
                logger.error(f"Error usando knowledge.json para optimización: {e}")

    except Exception as e:
        logger.error(f"Error en optimización Python: {e}", exc_info=True)
    
    return result


def detect_patterns(code: str) -> List[Dict[str, Any]]:
    """Detecta patrones problemáticos"""
    patterns = []
    try:
        if re.search(r'\bprint\s*\(', code):
            patterns.append({"type": "print_usage", "severity": "info"})
        if re.search(r'except\s*:', code):
            patterns.append({"type": "bare_except", "severity": "warning"})
        if re.search(r'==\s*None\b|!=\s*None\b', code):
            patterns.append({"type": "none_comparison", "severity": "warning"})
    except Exception as e:
        logger.error(f"Error detectando patrones: {e}")
    return patterns
