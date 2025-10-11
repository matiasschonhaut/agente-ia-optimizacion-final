#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interfaz web Dash para Agente IA de Optimización de Código
"""

import os
import sys
import json
import logging
import requests
import importlib.util
from datetime import datetime
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc

# Configuración de paths
BASE_PATH = os.environ.get('APP_BASE_PATH', '/app/base')
SOURCE_PATH = os.environ.get('APP_SOURCE_PATH', '/app/source')
KNOWLEDGE_BASE_PATH = os.environ.get('APP_KNOWLEDGE_BASE_PATH', '/app/knowledge_base')
LOGS_PATH = os.environ.get('APP_LOGS_PATH', '/app/logs')

# Configuración de Ollama - usar 0.0.0.0 consistentemente
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://0.0.0.0:11434')
MODEL_NAME = os.environ.get('MODEL_NAME', 'codellama:7b')

# Crear directorios
for path in [BASE_PATH, SOURCE_PATH, KNOWLEDGE_BASE_PATH, LOGS_PATH]:
    os.makedirs(path, exist_ok=True)

# Configuración de logging
logging.basicConfig(
    filename=os.path.join(LOGS_PATH, "dash.log"),
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Añadir paths
if SOURCE_PATH not in sys.path:
    sys.path.insert(0, SOURCE_PATH)
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

# Importar agent desde agent-ollama.py
try:
    spec = importlib.util.spec_from_file_location(
        "agent_ollama", 
        os.path.join(BASE_PATH, "agent-ollama.py")
    )
    if spec and spec.loader:
        agent_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(agent_module)
        CodeOptimizationAgent = agent_module.CodeOptimizationAgent
        logger.info("Módulo agent-ollama.py cargado correctamente")
    else:
        logger.error("No se pudo crear spec para agent-ollama.py")
        CodeOptimizationAgent = None
except Exception as e:
    logger.error(f"Error cargando agent-ollama.py: {e}")
    CodeOptimizationAgent = None

# Inicializar aplicación
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Agente IA - Optimización de Código"
server = app.server

# Inicializar agente
try:
    if CodeOptimizationAgent:
        agent = CodeOptimizationAgent()
        logger.info("Agente inicializado correctamente")
    else:
        agent = None
        logger.error("CodeOptimizationAgent no disponible")
except Exception as e:
    logger.error(f"Error inicializando agente: {e}")
    agent = None

# Layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Agente IA de Optimización de Código", className="text-center mb-4"),
            html.Hr()
        ], width=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Configuración"),
                dbc.CardBody([
                    dbc.Label("Lenguaje:"),
                    dcc.Dropdown(
                        id="language-select",
                        options=[
                            {"label": "Python", "value": "python"},
                            {"label": "JavaScript", "value": "javascript"},
                            {"label": "R", "value": "r"}
                        ],
                        value="python",
                        className="mb-3"
                    ),
                    dbc.Button("Verificar Conexión", id="check-btn", color="info", className="w-100")
                ])
            ])
        ], width=3),
        
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Código a Optimizar"),
                dbc.CardBody([
                    dcc.Textarea(
                        id="code-input",
                        style={
                            "width": "100%",
                            "height": 400,
                            "fontFamily": "monospace",
                            "fontSize": "14px"
                        },
                        placeholder="Pega tu código aquí..."
                    ),
                    dbc.ButtonGroup([
                        dbc.Button("Analizar", id="analyze-btn", color="primary"),
                        dbc.Button("Optimizar", id="optimize-btn", color="success"),
                        dbc.Button("Limpiar", id="clear-btn", color="danger")
                    ], className="mt-3 w-100")
                ])
            ])
        ], width=9)
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            html.Div(id="status-output"),
            html.Div(id="results-output")
        ], width=12)
    ]),
    
    dcc.Store(id="analysis-store")
], fluid=True)

# Callbacks
@app.callback(
    Output("status-output", "children"),
    Input("check-btn", "n_clicks")
)
def check_connection(n_clicks):
    if not n_clicks:
        return ""
    
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            
            if MODEL_NAME in model_names:
                return dbc.Alert(f"✓ Modelo {MODEL_NAME} disponible", color="success")
            else:
                available = ', '.join(model_names) if model_names else 'ninguno'
                return dbc.Alert(f"Modelos disponibles: {available}", color="warning")
    except requests.exceptions.ConnectionError:
        return dbc.Alert("Error: No se puede conectar con Ollama. Verifique que el servicio esté activo.", color="danger")
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger")

@app.callback(
    [Output("analysis-store", "data"),
     Output("results-output", "children", allow_duplicate=True)],
    Input("analyze-btn", "n_clicks"),
    [State("code-input", "value"),
     State("language-select", "value")],
    prevent_initial_call=True
)
def analyze_code(n_clicks, code, language):
    if not n_clicks or not code:
        return None, ""
    
    if not agent:
        return None, dbc.Alert("Agente no inicializado", color="danger")
    
    try:
        result = agent.analyze_code(code, language)
        
        if result["status"] == "success":
            analysis = result.get("analysis", {})
            
            # Construir salida visual
            cards = []
            
            # Métricas
            if analysis.get("metrics"):
                metrics_items = []
                for key, value in analysis["metrics"].items():
                    metrics_items.append(html.Li(f"{key.replace('_', ' ').title()}: {value}"))
                
                cards.append(
                    dbc.Card([
                        dbc.CardHeader("Métricas de Código"),
                        dbc.CardBody(html.Ul(metrics_items))
                    ], className="mb-3")
                )
            
            # Problemas detectados
            if analysis.get("issues"):
                issue_items = []
                for issue in analysis["issues"][:10]:  # Limitar a 10 issues
                    severity_color = {
                        "error": "danger",
                        "warning": "warning",
                        "info": "info"
                    }.get(issue.get("severity", "info"), "info")
                    
                    issue_text = f"{issue.get('type', 'issue')}: {issue.get('message', 'Sin descripción')}"
                    if issue.get("line"):
                        issue_text = f"Línea {issue['line']} - {issue_text}"
                    
                    issue_items.append(
                        dbc.Alert(issue_text, color=severity_color, className="mb-2")
                    )
                
                cards.append(
                    dbc.Card([
                        dbc.CardHeader(f"Problemas Detectados ({len(analysis['issues'])} total)"),
                        dbc.CardBody(issue_items if issue_items else html.P("No se detectaron problemas"))
                    ], className="mb-3")
                )
            
            # Sugerencias IA
            if analysis.get("ai_suggestions"):
                cards.append(
                    dbc.Card([
                        dbc.CardHeader("Sugerencias del Modelo IA"),
                        dbc.CardBody(html.P(analysis["ai_suggestions"]))
                    ], className="mb-3")
                )
            
            # Estado de sintaxis
            syntax_status = "✓ Sintaxis válida" if analysis.get("syntax_valid", True) else "✗ Error de sintaxis"
            syntax_color = "success" if analysis.get("syntax_valid", True) else "danger"
            
            output = html.Div([
                html.H5("Análisis Completado", className="mb-3"),
                dbc.Alert(syntax_status, color=syntax_color),
                *cards
            ])
            
            return result, output
        else:
            return None, dbc.Alert(f"Error: {result.get('message', 'Error desconocido')}", color="danger")
            
    except Exception as e:
        logger.error(f"Error en análisis: {e}")
        return None, dbc.Alert(f"Error: {str(e)}", color="danger")

@app.callback(
    Output("results-output", "children"),
    Input("optimize-btn", "n_clicks"),
    [State("code-input", "value"),
     State("language-select", "value")],
    prevent_initial_call=True
)
def optimize_code(n_clicks, code, language):
    if not n_clicks or not code:
        return ""
    
    if not agent:
        return dbc.Alert("Agente no inicializado", color="danger")
    
    try:
        result = agent.optimize_code(code, language)
        
        if result["status"] == "success":
            optimized_code = result.get("optimized_code", code)
            
            # Determinar si hubo cambios
            code_changed = optimized_code.strip() != code.strip()
            
            cards = []
            
            # Código optimizado
            cards.append(
                dbc.Card([
                    dbc.CardHeader("Código Optimizado"),
                    dbc.CardBody([
                        dcc.Textarea(
                            value=optimized_code,
                            style={
                                "width": "100%",
                                "height": 300,
                                "fontFamily": "monospace",
                                "fontSize": "14px"
                            },
                            readOnly=True
                        ),
                        dbc.Button(
                            "Copiar al área de entrada", 
                            id="copy-optimized-btn",
                            color="secondary",
                            size="sm",
                            className="mt-2"
                        ) if code_changed else None
                    ])
                ], className="mb-3")
            )
            
            # Mejoras aplicadas
            if result.get("improvements"):
                improvement_items = []
                for imp in result["improvements"]:
                    imp_type = imp.get("type", "mejora")
                    imp_tool = imp.get("tool", "")
                    imp_text = f"{imp_type.replace('_', ' ').title()}"
                    if imp_tool:
                        imp_text += f" (usando {imp_tool})"
                    improvement_items.append(html.Li(imp_text))
                
                cards.append(
                    dbc.Card([
                        dbc.CardHeader("Mejoras Aplicadas"),
                        dbc.CardBody(html.Ul(improvement_items))
                    ], className="mb-3")
                )
            
            # Sugerencias adicionales
            if result.get("suggestions"):
                suggestion_items = [html.Li(sug) for sug in result["suggestions"]]
                cards.append(
                    dbc.Card([
                        dbc.CardHeader("Sugerencias Adicionales"),
                        dbc.CardBody(html.Ul(suggestion_items))
                    ], className="mb-3")
                )
            
            # Estado general
            status_text = "✓ Optimización completada" if code_changed else "✓ El código ya está optimizado"
            status_color = "success" if code_changed else "info"
            
            output = html.Div([
                html.H5("Optimización Completada", className="mb-3"),
                dbc.Alert(status_text, color=status_color),
                *cards
            ])
            
            return output
        else:
            return dbc.Alert(f"Error: {result.get('message', 'Error desconocido')}", color="danger")
            
    except Exception as e:
        logger.error(f"Error en optimización: {e}")
        return dbc.Alert(f"Error: {str(e)}", color="danger")

@app.callback(
    [Output("code-input", "value"),
     Output("results-output", "children", allow_duplicate=True)],
    Input("clear-btn", "n_clicks"),
    prevent_initial_call=True
)
def clear_all(n_clicks):
    if n_clicks:
        return "", ""
    return dash.no_update, dash.no_update

# Callback adicional para copiar código optimizado
@app.callback(
    Output("code-input", "value", allow_duplicate=True),
    Input("copy-optimized-btn", "n_clicks"),
    State("results-output", "children"),
    prevent_initial_call=True
)
def copy_optimized_to_input(n_clicks, results_children):
    if n_clicks and results_children:
        try:
            # Buscar el textarea con el código optimizado en la estructura
            for child in results_children['props']['children']:
                if isinstance(child, dict) and child.get('type') == 'Card':
                    card_body = child.get('props', {}).get('children', [])
                    for card_child in card_body:
                        if isinstance(card_child, dict) and card_child.get('props', {}).get('children'):
                            body_children = card_child['props']['children']
                            if isinstance(body_children, list):
                                for elem in body_children:
                                    if isinstance(elem, dict) and elem.get('type') == 'Textarea':
                                        return elem['props']['value']
        except:
            pass
    return dash.no_update

if __name__ == "__main__":
    logger.info("Iniciando aplicación Dash")
    logger.info(f"Configuración: OLLAMA_BASE_URL={OLLAMA_BASE_URL}, MODEL_NAME={MODEL_NAME}")
    logger.info(f"Paths: BASE={BASE_PATH}, SOURCE={SOURCE_PATH}")
    
    # Verificar archivos críticos
    agent_path = os.path.join(BASE_PATH, "agent-ollama.py")
    if os.path.exists(agent_path):
        logger.info(f"✓ agent-ollama.py encontrado en {agent_path}")
    else:
        logger.error(f"✗ agent-ollama.py NO encontrado en {agent_path}")
    
    # Verificar módulos source
    for module in ["source-python-ollama.py", "source-javascript-ollama.py", "source-r-ollama.py"]:
        module_path = os.path.join(SOURCE_PATH, module)
        if os.path.exists(module_path):
            logger.info(f"✓ {module} encontrado")
        else:
            logger.error(f"✗ {module} NO encontrado")
    
    app.run_server(host="0.0.0.0", port=8050, debug=False)