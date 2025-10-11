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
from typing import Dict, List, Any
import logging

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

# Ejecutar verificación al cargar el módulo
check_tools()


def analyze(code: str) -> Dict[str, Any]:
    """Analiza código Python - función principal del módulo"""
    results = {
        "syntax_valid": False,
        "metrics": {},
        "issues": [],
        "patterns": []
    }
    
    try:
        # Validar sintaxis
        ast.parse(code)
        results["syntax_valid"] = True
        logger.debug("Sintaxis Python válida")
        
        # Métricas básicas
        lines = code.split('\n')
        results["metrics"] = {
            "total_lines": len(lines),
            "code_lines": sum(1 for l in lines if l.strip() and not l.strip().startswith('#')),
            "comment_lines": sum(1 for l in lines if l.strip().startswith('#')),
            "function_count": len(re.findall(r'def\s+\w+\s*\(', code)),
            "class_count": len(re.findall(r'class\s+\w+\s*[\(:]', code))
        }
        logger.debug(f"Métricas calculadas: {results['metrics']}")
        
        # Detectar patrones problemáticos
        results["patterns"] = detect_patterns(code)
        if results["patterns"]:
            logger.info(f"Patrones detectados: {len(results['patterns'])}")
        
        # Pylint si está disponible
        if TOOLS_AVAILABLE['pylint']:
            issues = run_pylint(code)
            results["issues"].extend(issues[:10])
            logger.info(f"Pylint encontró {len(issues)} issues")
        
        # Flake8 si está disponible y pylint no lo está
        elif TOOLS_AVAILABLE['flake8']:
            issues = run_flake8(code)
            results["issues"].extend(issues[:10])
            logger.info(f"Flake8 encontró {len(issues)} issues")
        
    except SyntaxError as e:
        results["issues"].append({
            "type": "syntax_error",
            "line": e.lineno,
            "message": str(e),
            "severity": "error"
        })
        logger.info(f"Error de sintaxis detectado: {e}")
    except Exception as e:
        logger.error(f"Error en análisis Python: {e}", exc_info=True)
        results["issues"].append({
            "type": "analysis_error",
            "message": str(e),
            "severity": "error"
        })
    
    return results


def optimize(code: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Optimiza código Python - función principal del módulo"""
    result = {
        "code": code,
        "suggestions": [],
        "improvements": []
    }
    
    try:
        # Solo optimizar si la sintaxis es válida
        analysis_data = analysis.get("analysis", {})
        if not analysis_data.get("syntax_valid", False):
            result["suggestions"].append("Corrija los errores de sintaxis antes de optimizar")
            return result
        
        # Black formatting
        if TOOLS_AVAILABLE['black']:
            formatted = format_with_black(code)
            if formatted and formatted != code:
                result["code"] = formatted
                result["improvements"].append({
                    "type": "formatting",
                    "tool": "black"
                })
                logger.info("Código formateado con Black")
        
        # isort para imports
        if TOOLS_AVAILABLE['isort']:
            sorted_code = sort_imports(result["code"])
            if sorted_code and sorted_code != result["code"]:
                result["code"] = sorted_code
                result["improvements"].append({
                    "type": "import_sorting",
                    "tool": "isort"
                })
                logger.info("Imports ordenados con isort")
        
        # autopep8 si black no está disponible
        if not TOOLS_AVAILABLE['black'] and TOOLS_AVAILABLE['autopep8']:
            formatted = format_with_autopep8(result["code"])
            if formatted and formatted != result["code"]:
                result["code"] = formatted
                result["improvements"].append({
                    "type": "formatting",
                    "tool": "autopep8"
                })
                logger.info("Código formateado con autopep8")
        
        # Sugerencias basadas en patrones
        for pattern in analysis_data.get("patterns", []):
            if pattern["type"] == "missing_docstring":
                result["suggestions"].append("Agregar docstrings a funciones y clases")
            elif pattern["type"] == "long_line":
                result["suggestions"].append("Considerar dividir líneas muy largas (>88 caracteres)")
            elif pattern["type"] == "complex_function":
                result["suggestions"].append("Considerar refactorizar funciones complejas")
        
        # Sugerencias basadas en issues
        error_count = sum(1 for issue in analysis_data.get("issues", []) 
                         if issue.get("severity") == "error")
        warning_count = sum(1 for issue in analysis_data.get("issues", []) 
                           if issue.get("severity") == "warning")
        
        if error_count > 0:
            result["suggestions"].append(f"Resolver {error_count} errores detectados por el linter")
        if warning_count > 0:
            result["suggestions"].append(f"Revisar {warning_count} advertencias del linter")
        
        if result["suggestions"]:
            logger.info(f"Generadas {len(result['suggestions'])} sugerencias")
    
    except Exception as e:
        logger.error(f"Error en optimización Python: {e}", exc_info=True)
    
    return result


def detect_patterns(code: str) -> List[Dict[str, Any]]:
    """Detecta patrones problemáticos en el código"""
    patterns = []
    
    try:
        # Importar re si no está importado
        import re
        
        # Funciones sin docstring
        functions = re.findall(r'def\s+(\w+)\s*\([^)]*\):\s*\n(?!\s*""")', code)
        if functions:
            patterns.append({
                "type": "missing_docstring",
                "severity": "info",
                "count": len(functions)
            })
        
        # Líneas muy largas
        long_lines = [i+1 for i, line in enumerate(code.split('\n')) if len(line) > 88]
        if long_lines:
            patterns.append({
                "type": "long_line",
                "severity": "info",
                "lines": long_lines[:5]  # Solo las primeras 5
            })
        
        # Uso de print() en lugar de logging
        if re.search(r'\bprint\s*\(', code):
            patterns.append({
                "type": "print_usage",
                "severity": "info"
            })
        
        # except sin tipo específico
        if re.search(r'except\s*:', code):
            patterns.append({
                "type": "bare_except",
                "severity": "warning"
            })
        
        # Comparación con None usando ==
        if re.search(r'==\s*None\b|!=\s*None\b', code):
            patterns.append({
                "type": "none_comparison",
                "severity": "warning"
            })
        
    except Exception as e:
        logger.error(f"Error detectando patrones: {e}")
    
    return patterns


def run_pylint(code: str) -> List[Dict[str, Any]]:
    """Ejecuta pylint en el código"""
    issues = []
    temp_file = None
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        result = subprocess.run(
            ['pylint', '--output-format=json', temp_file],
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            try:
                pylint_results = json.loads(result.stdout)
                for issue in pylint_results:
                    issues.append({
                        "type": "pylint",
                        "line": issue.get('line', 0),
                        "column": issue.get('column', 0),
                        "message": issue.get('message', ''),
                        "severity": "error" if issue.get('type') == 'error' else "warning",
                        "symbol": issue.get('symbol', '')
                    })
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando resultado de pylint: {e}")
        
    except subprocess.CalledProcessError as e:
        logger.debug(f"Pylint retornó código no-cero (esperado): {e.returncode}")
    except Exception as e:
        logger.error(f"Error ejecutando pylint: {e}")
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.error(f"Error eliminando archivo temporal: {e}")
    
    return issues


def run_flake8(code: str) -> List[Dict[str, Any]]:
    """Ejecuta flake8 como alternativa a pylint"""
    issues = []
    temp_file = None
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        result = subprocess.run(
            ['flake8', '--format=json', temp_file],
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            # flake8 no tiene formato JSON nativo, parsear salida
            for line in result.stdout.strip().split('\n'):
                if line and ':' in line:
                    parts = line.split(':', 3)
                    if len(parts) >= 4:
                        try:
                            line_num = int(parts[1])
                            col_num = int(parts[2])
                            message = parts[3].strip()
                            issues.append({
                                "type": "flake8",
                                "line": line_num,
                                "column": col_num,
                                "message": message,
                                "severity": "warning"
                            })
                        except ValueError:
                            pass
        
    except Exception as e:
        logger.error(f"Error ejecutando flake8: {e}")
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.error(f"Error eliminando archivo temporal: {e}")
    
    return issues


def format_with_black(code: str) -> str:
    """Formatea código con black"""
    try:
        result = subprocess.run(
            ['black', '--quiet', '-'],
            input=code,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout:
            logger.debug("Código formateado exitosamente con Black")
            return result.stdout
        elif result.stderr:
            logger.warning(f"Black warning: {result.stderr}")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Error ejecutando Black: {e}")
    except Exception as e:
        logger.error(f"Error inesperado en Black: {e}")
    
    return code


def sort_imports(code: str) -> str:
    """Ordena imports con isort"""
    try:
        result = subprocess.run(
            ['isort', '-'],
            input=code,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout:
            logger.debug("Imports ordenados exitosamente con isort")
            return result.stdout
        elif result.stderr:
            logger.warning(f"isort warning: {result.stderr}")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Error ejecutando isort: {e}")
    except Exception as e:
        logger.error(f"Error inesperado en isort: {e}")
    
    return code


def format_with_autopep8(code: str) -> str:
    """Formatea código con autopep8 como alternativa a black"""
    try:
        result = subprocess.run(
            ['autopep8', '-'],
            input=code,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout:
            logger.debug("Código formateado exitosamente con autopep8")
            return result.stdout
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Error ejecutando autopep8: {e}")
    except Exception as e:
        logger.error(f"Error inesperado en autopep8: {e}")
    
    return code