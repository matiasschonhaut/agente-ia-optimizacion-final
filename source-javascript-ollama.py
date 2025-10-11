#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de análisis y optimización para JavaScript
"""

import re
import json
import subprocess
import tempfile
import os
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# Verificar herramientas
TOOLS_AVAILABLE = {
    'node': False,
    'eslint': False,
    'prettier': False
}

def check_tools():
    """Verifica disponibilidad de herramientas"""
    # Verificar Node.js
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, check=True, text=True)
        TOOLS_AVAILABLE['node'] = True
        logger.info(f"Node.js disponible: {result.stdout.strip()}")
        
        if TOOLS_AVAILABLE['node']:
            # Verificar eslint y prettier usando npx consistentemente
            for tool in ['eslint', 'prettier']:
                try:
                    result = subprocess.run(
                        ['npx', '--no-install', tool, '--version'], 
                        capture_output=True, 
                        check=True,
                        text=True
                    )
                    TOOLS_AVAILABLE[tool] = True
                    logger.info(f"{tool} disponible: {result.stdout.strip()}")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"{tool} no disponible: {e}")
                except Exception as e:
                    logger.error(f"Error verificando {tool}: {e}")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Node.js no disponible: {e}")
    except Exception as e:
        logger.error(f"Error verificando Node.js: {e}")

# Ejecutar verificación al cargar el módulo
check_tools()


def analyze(code: str) -> Dict[str, Any]:
    """Analiza código JavaScript"""
    results = {
        "syntax_valid": True,
        "metrics": {},
        "issues": [],
        "patterns": []
    }
    
    try:
        # Validación básica de sintaxis
        syntax_check = check_syntax(code)
        results["syntax_valid"] = syntax_check["valid"]
        if not syntax_check["valid"]:
            results["issues"].append({
                "type": "syntax_error",
                "message": syntax_check["error"],
                "severity": "error"
            })
            logger.info(f"Error de sintaxis detectado: {syntax_check['error']}")
        
        # Métricas
        lines = code.split('\n')
        results["metrics"] = {
            "total_lines": len(lines),
            "code_lines": count_code_lines(lines),
            "comment_lines": count_comment_lines(lines),
            "function_count": len(re.findall(r'function\s+\w+|=>\s*{', code))
        }
        logger.debug(f"Métricas calculadas: {results['metrics']}")
        
        # Detectar patrones problemáticos
        results["patterns"] = detect_patterns(code)
        if results["patterns"]:
            logger.info(f"Patrones detectados: {len(results['patterns'])}")
        
        # ESLint si está disponible
        if TOOLS_AVAILABLE['eslint']:
            eslint_issues = run_eslint(code)
            results["issues"].extend(eslint_issues[:10])
            logger.info(f"ESLint encontró {len(eslint_issues)} issues")
        else:
            logger.debug("ESLint no disponible para análisis")
        
    except Exception as e:
        logger.error(f"Error en análisis JS: {e}", exc_info=True)
        results["issues"].append({
            "type": "analysis_error",
            "message": str(e),
            "severity": "error"
        })
    
    return results


def optimize(code: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Optimiza código JavaScript"""
    result = {
        "code": code,
        "suggestions": [],
        "improvements": []
    }
    
    try:
        # Prettier si está disponible
        if TOOLS_AVAILABLE['prettier']:
            formatted = format_with_prettier(code)
            if formatted and formatted != code:
                result["code"] = formatted
                result["improvements"].append({
                    "type": "formatting",
                    "tool": "prettier"
                })
                logger.info("Código formateado con Prettier")
        else:
            logger.debug("Prettier no disponible para formateo")
        
        # Aplicar optimizaciones básicas
        optimized = apply_basic_optimizations(result["code"])
        if optimized != result["code"]:
            result["code"] = optimized
            result["improvements"].append({
                "type": "basic_optimizations"
            })
            logger.info("Optimizaciones básicas aplicadas")
        
        # Sugerencias basadas en patrones
        for pattern in analysis.get("analysis", {}).get("patterns", []):
            if pattern["type"] == "var_usage":
                result["suggestions"].append("Usar const/let en lugar de var")
            elif pattern["type"] == "loose_equality":
                result["suggestions"].append("Usar === en lugar de ==")
            elif pattern["type"] == "eval_usage":
                result["suggestions"].append("Evitar el uso de eval() por razones de seguridad")
        
        if result["suggestions"]:
            logger.info(f"Generadas {len(result['suggestions'])} sugerencias")
        
    except Exception as e:
        logger.error(f"Error en optimización JS: {e}", exc_info=True)
    
    return result


def check_syntax(code: str) -> Dict[str, Any]:
    """Valida sintaxis básica"""
    stack = []
    pairs = {'(': ')', '[': ']', '{': '}'}
    
    in_string = False
    string_char = None
    escape_next = False
    
    try:
        for i, char in enumerate(code):
            # Manejar escapes
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            # Manejar strings
            if char in ['"', "'", '`'] and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
                continue
            
            if in_string:
                continue
            
            # Verificar paréntesis, corchetes y llaves
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack:
                    return {
                        "valid": False,
                        "error": f"Símbolo '{char}' sin apertura en posición {i}"
                    }
                opener = stack.pop()
                if pairs[opener] != char:
                    return {
                        "valid": False,
                        "error": f"Símbolos no coinciden: '{opener}' y '{char}' en posición {i}"
                    }
        
        if stack:
            return {
                "valid": False,
                "error": f"Símbolo '{stack[-1]}' sin cerrar"
            }
        
        if in_string:
            return {
                "valid": False,
                "error": f"String sin cerrar (delimitador: {string_char})"
            }
        
        return {"valid": True, "error": None}
        
    except Exception as e:
        logger.error(f"Error en verificación de sintaxis: {e}")
        return {
            "valid": False,
            "error": f"Error interno: {str(e)}"
        }


def count_code_lines(lines: List[str]) -> int:
    """Cuenta líneas de código"""
    count = 0
    in_comment = False
    
    try:
        for line in lines:
            stripped = line.strip()
            
            # Detectar inicio de comentario multilinea
            if "/*" in stripped and not in_comment:
                in_comment = True
                # Si el comentario se cierra en la misma línea
                if "*/" in stripped and stripped.index("*/") > stripped.index("/*"):
                    in_comment = False
            
            # Contar línea si no es comentario ni está vacía
            if not in_comment and stripped and not stripped.startswith('//'):
                count += 1
            
            # Detectar fin de comentario multilinea
            if "*/" in stripped and in_comment:
                in_comment = False
        
    except Exception as e:
        logger.error(f"Error contando líneas de código: {e}")
    
    return count


def count_comment_lines(lines: List[str]) -> int:
    """Cuenta líneas de comentarios"""
    count = 0
    in_comment = False
    
    try:
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith('//'):
                count += 1
            elif "/*" in stripped and not in_comment:
                in_comment = True
                count += 1
            elif in_comment:
                count += 1
                if "*/" in stripped:
                    in_comment = False
        
    except Exception as e:
        logger.error(f"Error contando líneas de comentarios: {e}")
    
    return count


def detect_patterns(code: str) -> List[Dict[str, Any]]:
    """Detecta patrones problemáticos"""
    patterns = []
    
    try:
        # var usage
        if re.search(r'\bvar\s+', code):
            patterns.append({
                "type": "var_usage",
                "severity": "info"
            })
        
        # == en lugar de ===
        if re.search(r'[^=!]==[^=]', code):
            patterns.append({
                "type": "loose_equality",
                "severity": "warning"
            })
        
        # eval usage
        if 'eval(' in code:
            patterns.append({
                "type": "eval_usage",
                "severity": "error"
            })
        
        # with statement (deprecated)
        if re.search(r'\bwith\s*\(', code):
            patterns.append({
                "type": "with_usage",
                "severity": "warning"
            })
        
        # document.write (problematic)
        if 'document.write' in code:
            patterns.append({
                "type": "document_write",
                "severity": "warning"
            })
        
    except Exception as e:
        logger.error(f"Error detectando patrones: {e}")
    
    return patterns


def run_eslint(code: str) -> List[Dict[str, Any]]:
    """Ejecuta ESLint si está disponible"""
    issues = []
    temp_file = None
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # Usar npx consistentemente con --no-install para evitar instalaciones
        result = subprocess.run(
            ['npx', '--no-install', 'eslint', '--format=json', temp_file],
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            try:
                eslint_results = json.loads(result.stdout)
                if eslint_results and len(eslint_results) > 0:
                    for message in eslint_results[0].get('messages', []):
                        issues.append({
                            "type": "eslint",
                            "line": message.get('line', 0),
                            "column": message.get('column', 0),
                            "message": message.get('message', ''),
                            "severity": "error" if message.get('severity') == 2 else "warning",
                            "rule": message.get('ruleId', 'unknown')
                        })
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando resultado de ESLint: {e}")
        
    except subprocess.CalledProcessError as e:
        logger.warning(f"ESLint retornó código de error: {e.returncode}")
    except Exception as e:
        logger.error(f"Error ejecutando ESLint: {e}")
    finally:
        # Limpiar archivo temporal
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.error(f"Error eliminando archivo temporal: {e}")
    
    return issues


def format_with_prettier(code: str) -> str:
    """Formatea con prettier"""
    try:
        # Usar npx consistentemente con --no-install
        result = subprocess.run(
            ['npx', '--no-install', 'prettier', '--parser=babel', '--no-semi', '--single-quote'],
            input=code,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout:
            logger.debug("Código formateado exitosamente con Prettier")
            return result.stdout
        else:
            if result.stderr:
                logger.warning(f"Prettier warning/error: {result.stderr}")
                
    except subprocess.CalledProcessError as e:
        logger.error(f"Error ejecutando Prettier: {e}")
    except Exception as e:
        logger.error(f"Error inesperado en Prettier: {e}")
    
    return code


def apply_basic_optimizations(code: str) -> str:
    """Aplica optimizaciones básicas"""
    try:
        original_code = code
        
        # Reemplazar var con let (cuidando contextos)
        code = re.sub(r'\bvar\s+', 'let ', code)
        
        # Reemplazar == con === (cuidando no afectar === existentes o comentarios)
        # Primero encontrar todas las ocurrencias de == que no son ===
        code = re.sub(r'([^=!])=([^=])', r'\1==\2', code)
        code = re.sub(r'([^=!])==([^=])', r'\1===\2', code)
        
        # Reemplazar != con !== (cuidando contextos)
        code = re.sub(r'([^=!])!=([^=])', r'\1!==\2', code)
        
        if code != original_code:
            logger.info("Optimizaciones básicas aplicadas al código")
        
        return code
        
    except Exception as e:
        logger.error(f"Error aplicando optimizaciones básicas: {e}")
        return code