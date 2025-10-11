#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de análisis y optimización para R
"""

import re
import subprocess
import tempfile
import os
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# Verificar R y herramientas
R_AVAILABLE = False
TOOLS_AVAILABLE = {
    'lintr': False,
    'styler': False
}

def check_r_installation():
    """Verifica instalación de R y paquetes"""
    global R_AVAILABLE
    
    try:
        result = subprocess.run(['R', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            R_AVAILABLE = True
            logger.info("R está disponible")
            
            # Verificar paquetes R
            for pkg in ['lintr', 'styler']:
                if check_r_package(pkg):
                    TOOLS_AVAILABLE[pkg] = True
                    logger.info(f"Paquete R '{pkg}' disponible")
                else:
                    logger.debug(f"Paquete R '{pkg}' no disponible")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        logger.warning("R no está disponible o no responde")
    except Exception as e:
        logger.error(f"Error verificando R: {e}")

def check_r_package(package: str) -> bool:
    """Verifica si un paquete de R está instalado"""
    try:
        cmd = ['R', '--slave', '--vanilla', '-e', f'if(requireNamespace("{package}", quietly=TRUE)) cat("OK") else cat("NO")']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() == "OK"
    except:
        return False

# Ejecutar verificación al cargar el módulo
check_r_installation()


def analyze(code: str) -> Dict[str, Any]:
    """Analiza código R"""
    results = {
        "syntax_valid": True,
        "metrics": {},
        "issues": [],
        "patterns": []
    }
    
    try:
        # Validación de sintaxis
        if R_AVAILABLE:
            syntax_check = check_r_syntax(code)
            results["syntax_valid"] = syntax_check["valid"]
            if not syntax_check["valid"]:
                results["issues"].append({
                    "type": "syntax_error",
                    "message": syntax_check["error"],
                    "severity": "error"
                })
                logger.info(f"Error de sintaxis detectado: {syntax_check['error']}")
        
        # Métricas básicas
        lines = code.split('\n')
        results["metrics"] = {
            "total_lines": len(lines),
            "code_lines": count_code_lines(lines),
            "comment_lines": count_comment_lines(lines),
            "function_count": count_functions(code)
        }
        logger.debug(f"Métricas calculadas: {results['metrics']}")
        
        # Detectar patrones problemáticos
        results["patterns"] = detect_r_patterns(code)
        if results["patterns"]:
            logger.info(f"Patrones detectados: {len(results['patterns'])}")
        
        # lintr si está disponible
        if TOOLS_AVAILABLE['lintr'] and results["syntax_valid"]:
            lintr_issues = run_lintr(code)
            results["issues"].extend(lintr_issues[:10])
            if lintr_issues:
                logger.info(f"lintr encontró {len(lintr_issues)} issues")
        
    except Exception as e:
        logger.error(f"Error en análisis R: {e}", exc_info=True)
        results["issues"].append({
            "type": "analysis_error",
            "message": str(e),
            "severity": "error"
        })
    
    return results


def optimize(code: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Optimiza código R"""
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
        
        # styler si está disponible
        if TOOLS_AVAILABLE['styler']:
            styled = format_with_styler(code)
            if styled and styled != code:
                result["code"] = styled
                result["improvements"].append({
                    "type": "formatting",
                    "tool": "styler"
                })
                logger.info("Código formateado con styler")
        
        # Optimizaciones básicas
        optimized = apply_basic_optimizations(result["code"])
        if optimized != result["code"]:
            result["code"] = optimized
            result["improvements"].append({
                "type": "basic_optimizations"
            })
            logger.info("Optimizaciones básicas aplicadas")
        
        # Sugerencias basadas en patrones
        for pattern in analysis_data.get("patterns", []):
            if pattern["type"] == "t_f_usage":
                result["suggestions"].append("Usar TRUE/FALSE en lugar de T/F para mayor claridad")
            elif pattern["type"] == "attach_usage":
                result["suggestions"].append("Evitar attach(), usar with() o el operador $")
            elif pattern["type"] == "na_comparison":
                result["suggestions"].append("Usar is.na() para comparar con NA")
            elif pattern["type"] == "single_equals":
                result["suggestions"].append("Usar <- para asignación en lugar de =")
        
        # Sugerencias basadas en issues
        error_count = sum(1 for issue in analysis_data.get("issues", []) 
                         if issue.get("severity") == "error")
        warning_count = sum(1 for issue in analysis_data.get("issues", []) 
                           if issue.get("severity") == "warning")
        
        if error_count > 0:
            result["suggestions"].append(f"Resolver {error_count} errores detectados")
        if warning_count > 0:
            result["suggestions"].append(f"Revisar {warning_count} advertencias")
        
        if result["suggestions"]:
            logger.info(f"Generadas {len(result['suggestions'])} sugerencias")
        
    except Exception as e:
        logger.error(f"Error en optimización R: {e}", exc_info=True)
    
    return result


def check_r_syntax(code: str) -> Dict[str, Any]:
    """Verifica sintaxis con R"""
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.R', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # Comando R simplificado
        cmd = ['R', '--slave', '--vanilla', '-e', f'tryCatch(parse("{temp_file}"), error=function(e) cat("ERROR:", conditionMessage(e)))']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if 'ERROR:' in result.stdout:
            error_msg = result.stdout.split('ERROR:')[1].strip()
            return {"valid": False, "error": error_msg}
        
        return {"valid": True, "error": None}
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout verificando sintaxis R")
        return {"valid": True, "error": "Timeout en verificación"}
    except Exception as e:
        logger.error(f"Error verificando sintaxis: {e}")
        return {"valid": True, "error": None}
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except:
                pass


def count_code_lines(lines: List[str]) -> int:
    """Cuenta líneas de código (excluyendo comentarios y líneas vacías)"""
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            count += 1
    return count


def count_comment_lines(lines: List[str]) -> int:
    """Cuenta líneas de comentarios"""
    return sum(1 for line in lines if line.strip().startswith('#'))


def count_functions(code: str) -> int:
    """Cuenta definiciones de funciones en R"""
    # Patrones para funciones en R
    patterns = [
        r'(\w+)\s*<-\s*function\s*\(',  # nombre <- function(
        r'(\w+)\s*=\s*function\s*\(',    # nombre = function(
        r'function\s*\(',                 # funciones anónimas
    ]
    
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, code))
    
    return count


def detect_r_patterns(code: str) -> List[Dict[str, Any]]:
    """Detecta patrones problemáticos en R"""
    patterns = []
    
    try:
        # Uso de T/F en lugar de TRUE/FALSE
        if re.search(r'\b[TF]\b(?!\w)', code):
            patterns.append({
                "type": "t_f_usage",
                "severity": "info"
            })
        
        # attach()
        if re.search(r'\battach\s*\(', code):
            patterns.append({
                "type": "attach_usage",
                "severity": "warning"
            })
        
        # Comparación incorrecta con NA
        if re.search(r'[!=]=\s*NA\b', code):
            patterns.append({
                "type": "na_comparison",
                "severity": "error"
            })
        
        # Uso de = para asignación (fuera de llamadas a funciones)
        # Patrón simplificado para evitar falsos positivos
        if re.search(r'^\s*\w+\s*=\s*[^=]', code, re.MULTILINE):
            patterns.append({
                "type": "single_equals",
                "severity": "info"
            })
        
        # require() en lugar de library()
        if re.search(r'\brequire\s*\(', code):
            patterns.append({
                "type": "require_usage",
                "severity": "info"
            })
        
    except Exception as e:
        logger.error(f"Error detectando patrones: {e}")
    
    return patterns


def run_lintr(code: str) -> List[Dict[str, Any]]:
    """Ejecuta lintr si está disponible"""
    issues = []
    temp_file = None
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.R', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # Comando R simplificado para lintr
        r_code = f'''
library(lintr)
lints <- lint("{temp_file}")
if(length(lints) > 0) {{
    for(i in seq_along(lints)) {{
        l <- lints[[i]]
        cat(paste(l$line_number, l$type, l$message, sep="::"))
        cat("\\n")
    }}
}}
'''
        
        cmd = ['R', '--slave', '--vanilla', '-e', r_code]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if '::' in line and not line.startswith('Loading'):
                    parts = line.split('::', 2)
                    if len(parts) >= 3:
                        try:
                            issues.append({
                                "type": "lintr",
                                "line": int(parts[0]),
                                "message": parts[2],
                                "severity": "warning" if parts[1] == "style" else "error"
                            })
                        except ValueError:
                            pass
        
    except subprocess.TimeoutExpired:
        logger.warning("lintr timeout")
    except Exception as e:
        logger.error(f"Error ejecutando lintr: {e}")
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except:
                pass
    
    return issues


def format_with_styler(code: str) -> str:
    """Formatea con styler"""
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.R', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # Comando R simplificado para styler
        r_code = f'''
library(styler)
styled <- style_file("{temp_file}")
cat(readLines("{temp_file}"), sep="\\n")
'''
        
        cmd = ['R', '--slave', '--vanilla', '-e', r_code]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout:
            # Filtrar mensajes de carga de librerías
            lines = result.stdout.split('\n')
            clean_lines = [l for l in lines if not l.startswith('Loading') and not l.startswith('Attaching')]
            return '\n'.join(clean_lines)
            
    except subprocess.TimeoutExpired:
        logger.warning("styler timeout")
    except Exception as e:
        logger.error(f"Error ejecutando styler: {e}")
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except:
                pass
    
    return code


def apply_basic_optimizations(code: str) -> str:
    """Aplica optimizaciones básicas"""
    try:
        # Reemplazar T/F con TRUE/FALSE
        code = re.sub(r'\bT\b(?!\w)', 'TRUE', code)
        code = re.sub(r'\bF\b(?!\w)', 'FALSE', code)
        
        # Reemplazar comparaciones con NA
        code = re.sub(r'(\w+)\s*==\s*NA\b', r'is.na(\1)', code)
        code = re.sub(r'(\w+)\s*!=\s*NA\b', r'!is.na(\1)', code)
        
        # Reemplazar = con <- para asignaciones (cuidando no afectar argumentos)
        # Solo al inicio de línea o después de espacios/paréntesis
        code = re.sub(r'(^|\s|\()(\w+)\s*=\s*(?!=)', r'\1\2 <- ', code, flags=re.MULTILINE)
        
        logger.debug("Optimizaciones básicas aplicadas")
        
    except Exception as e:
        logger.error(f"Error aplicando optimizaciones: {e}")
    
    return code