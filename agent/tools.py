"""
Tool Definitions for Agent (LangChain native tools)
Define las herramientas que el agente puede usar (llamadas a MCPs)
"""

import requests
from typing import Dict, Any
from langchain_core.tools import tool
import config

# URLs de los MCPs
MCP_URLS = config.MCP_URLS


# ==============================================================================
# TOOLS (LangChain decorators)
# ==============================================================================

@tool
def trace_propagation(post_id: str) -> Dict[str, Any]:
    """Analizar como se propago un mensaje en la red. Calcula alcance, velocidad, profundidad del árbol de respuestas.

    Args:
        post_id: ID único del post/mensaje a analizar (ej: c6adb4630994bdee807d387382d526bc)
    """
    try:
        response = requests.get(
            f"{MCP_URLS['propagation']}/analisis/propagacion",
            params={"post_id": post_id},
            timeout=30
        )
        return response.json() if response.status_code == 200 else {
            "error": f"Error {response.status_code}",
            "details": response.text
        }
    except Exception as e:
        return {"error": "Connection error", "details": str(e)}


@tool
def analyze_sentiment() -> Dict[str, Any]:
    """Analizar los sentimientos en las conversaciones digitales. Retorna distribucion (POSITIVE, NEGATIVE, NEUTRAL, UNKNOWN) y sentimiento dominante."""
    try:
        response = requests.get(
            f"{MCP_URLS['sentiment']}/analisis/sentimiento",
            timeout=30
        )
        return response.json() if response.status_code == 200 else {
            "error": f"Error {response.status_code}",
            "details": response.text
        }
    except Exception as e:
        return {"error": "Connection error", "details": str(e)}


@tool
def get_influence_metrics() -> Dict[str, Any]:
    """Obtener metricas de influencia: top autores, posts mas comentados, autores mas activos, estadisticas generales."""
    try:
        response = requests.get(
            f"{MCP_URLS['influence']}/analisis/metricas",
            timeout=30
        )
        return response.json() if response.status_code == 200 else {
            "error": f"Error {response.status_code}",
            "details": response.text
        }
    except Exception as e:
        return {"error": "Connection error", "details": str(e)}


# ==============================================================================
# TOOLS LIST (for .bind_tools() in graph)
# ==============================================================================

TOOLS = [trace_propagation, analyze_sentiment, get_influence_metrics]


# ==============================================================================
# LEGACY: TOOLS_SCHEMA (for compatibility with existing code)
# ==============================================================================

def _get_legacy_schema():
    """Backward compatibility alias for tools schema."""
    return [
        {
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.args_schema.model_json_schema() if hasattr(t, 'args_schema') else {
                "type": "object",
                "properties": {}
            }
        }
        for t in TOOLS
    ]


# Lazy evaluation to support both old and new code patterns
TOOLS_SCHEMA = _get_legacy_schema()


# ==============================================================================
# TOOL ROUTER (Legacy, for backward compatibility)
# ==============================================================================

def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Router para ejecutar una herramienta por nombre (legacy function)."""
    tool_map = {t.name: t for t in TOOLS}

    if tool_name not in tool_map:
        return {
            "error": f"Unknown tool: {tool_name}",
            "available_tools": [t.name for t in TOOLS]
        }

    try:
        return tool_map[tool_name].invoke(tool_input)
    except Exception as e:
        return {"error": f"Tool execution error: {str(e)}"}
