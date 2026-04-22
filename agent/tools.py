"""
Tool Definitions for Agent
Define las herramientas que el agente puede usar (llamadas a MCPs)
"""

import requests
from typing import Optional, Dict, Any
import config

# URLs de los MCPs
MCP_URLS = config.MCP_URLS


# ==============================================================================
# PROPAGATION TOOL
# ==============================================================================

def trace_propagation(post_id: str) -> Dict[str, Any]:
    """
    Analizar la propagacion de un post

    Args:
        post_id: ID del post a analizar

    Returns:
        Resultado del MCP de propagacion
    """
    try:
        response = requests.get(
            f"{MCP_URLS['propagation']}/analisis/propagacion",
            params={"post_id": post_id},
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"Error {response.status_code}",
                "details": response.text
            }

    except Exception as e:
        return {
            "error": "Connection error",
            "details": str(e)
        }


# ==============================================================================
# SENTIMENT TOOL
# ==============================================================================

def analyze_sentiment() -> Dict[str, Any]:
    """
    Analizar sentimientos en las conversaciones

    Returns:
        Distribucion de sentimientos y dominante
    """
    try:
        response = requests.get(
            f"{MCP_URLS['sentiment']}/analisis/sentimiento",
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"Error {response.status_code}",
                "details": response.text
            }

    except Exception as e:
        return {
            "error": "Connection error",
            "details": str(e)
        }


# ==============================================================================
# INFLUENCE TOOL
# ==============================================================================

def get_influence_metrics() -> Dict[str, Any]:
    """
    Obtener metricas de influencia

    Returns:
        Top autores, top posts, estadisticas
    """
    try:
        response = requests.get(
            f"{MCP_URLS['influence']}/analisis/metricas",
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"Error {response.status_code}",
                "details": response.text
            }

    except Exception as e:
        return {
            "error": "Connection error",
            "details": str(e)
        }


# ==============================================================================
# TOOL SCHEMAS (para LLM tool calling)
# ==============================================================================

TOOLS_SCHEMA = [
    {
        "name": "trace_propagation",
        "description": "Analizar como se propago un mensaje en la red. Calcula alcance, velocidad, profundidad del arbol de respuestas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "post_id": {
                    "type": "string",
                    "description": "ID unico del post/mensaje a analizar (ej: c6adb4630994bdee807d387382d526bc)"
                }
            },
            "required": ["post_id"]
        }
    },
    {
        "name": "analyze_sentiment",
        "description": "Analizar los sentimientos en las conversaciones digitales. Retorna distribucion (POSITIVE, NEGATIVE, NEUTRAL, UNKNOWN) y sentimiento dominante.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_influence_metrics",
        "description": "Obtener metricas de influencia: top autores, posts mas comentados, autores mas activos, estadisticas generales.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]


# ==============================================================================
# TOOL ROUTER (para el agente)
# ==============================================================================

def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Router para ejecutar una herramienta por nombre

    Args:
        tool_name: Nombre de la herramienta
        tool_input: Parametros de entrada

    Returns:
        Resultado de la herramienta
    """
    if tool_name == "trace_propagation":
        return trace_propagation(tool_input.get("post_id", ""))

    elif tool_name == "analyze_sentiment":
        return analyze_sentiment()

    elif tool_name == "get_influence_metrics":
        return get_influence_metrics()

    else:
        return {
            "error": f"Unknown tool: {tool_name}",
            "available_tools": [t["name"] for t in TOOLS_SCHEMA]
        }
