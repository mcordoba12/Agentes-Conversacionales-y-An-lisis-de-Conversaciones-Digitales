"""
LangGraph State Graph for Conversational Agent
Define el flujo del agente y la orquestacion de tools
"""

import json
import re
from typing import Dict, Any, List, Union, Callable
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from .state import AgentStateDict
from .llm_factory import create_llm
from .memory import ConversationalMemory
from .tools import TOOLS, execute_tool, TOOLS_SCHEMA
from .prompts import (get_route_system_prompt, get_react_system_prompt, get_generate_system_prompt,
                      get_reflection_system_prompt, get_planning_system_prompt, get_hitl_approval_prompt)
from .cost_tracker import CostTracker
from .memory_backends import create_memory_backend
from observability import LocalTracer, RagasEvaluator
from security.injection_detector import detect_prompt_injection, get_injection_severity, RateLimiter
from security.pii_detector import mask_sensitive_data, detect_pii, load_usernames_from_loader
from security.audit_logger import AuditLogger
import config
import uuid
import time


# ==============================================================================
# DETECCIÓN DE INTENCIONES
# ==============================================================================

def detect_sentiment_intent(message: str) -> bool:
    """
    Detecta si el usuario pregunta por sentimiento GENERAL (sin texto específico)

    Ejemplos positivos:
    - "¿Cómo está el sentimiento?"
    - "¿Cuál es el sentimiento dominante?"
    - "¿La conversación es positiva o negativa?"
    - "¿Cómo está el clima?"
    - "Analiza los sentimientos"
    - "Sentimiento general"
    - "¿Qué sentimiento hay?"

    Ejemplos negativos (requieren texto):
    - "Analiza el sentimiento de esto: [texto]"
    - "¿Cuál es el sentimiento de [texto]?"
    """
    message_lower = message.lower().strip()

    # Palabras clave que indican sentimiento general
    sentiment_keywords = [
        "sentimiento",
        "sentimientos",
        "clima",
        "positivo",
        "negativo",
        "neutral"
    ]

    # Frases que indican sentimiento general (sin especificar texto)
    general_patterns = [
        r"¿cómo está.*sentimiento\??",
        r"¿cuál es.*sentimiento",
        r"sentimiento general",
        r"sentimientos en.*conversación",
        r"¿la conversación es.*positiva\?|negativa\?",
        r"¿cómo está el clima",
        r"analiza[r]? los sentimientos",
        r"cuéntame sobre el sentimiento",
        r"dame\s+.*sentimiento",
        r"^sentimiento",
    ]

    # Patrones que indican que SE PROPORCIONA texto específico
    specific_patterns = [
        r"analiza.*sentimiento de",
        r"sentimiento de\s+(?:este|ese|ese|mi|tu|su|el)",  # sentimiento DE algo
        r"este\s+sentimiento",
        r"mi\s+sentimiento",
        r"tu\s+sentimiento",
    ]

    # Si tiene patrón específico, NO es intención general
    for pattern in specific_patterns:
        if re.search(pattern, message_lower):
            return False

    # Si tiene patrón general Y alguna palabra clave, ES intención general
    for pattern in general_patterns:
        if re.search(pattern, message_lower):
            return True

    # Si tiene palabras clave de sentimiento pero sin contexto específico
    has_sentiment_keyword = any(kw in message_lower for kw in sentiment_keywords)

    # Si no hay indicios de que sea sobre un texto específico
    specific_indicators = ["esto", "eso", "texto", "frase", "párrafo", "mensaje", "comentario"]
    has_specific_indicator = any(ind in message_lower for ind in specific_indicators)

    if has_sentiment_keyword and not has_specific_indicator:
        # Verificar que no sea pregunta de seguimiento irrelevante
        if len(message) < 200:  # Mensaje corto + keyword = probablemente general
            return True

    return False


def detect_metrics_intent(message: str) -> bool:
    """
    Detecta si el usuario pregunta por métricas de influencia/impacto

    Ejemplos positivos:
    - "¿Quién escribió el post más comentado?"
    - "¿Cuál es el post más popular?"
    - "¿Quién es el usuario más influyente?"
    - "¿Cuál es el post con más impacto?"
    - "¿Quién es el autor más activo?"
    - "Top usuarios"
    - "¿Cuál es la publicación más comentada?"
    - "¿Quién escribió el post más impactante?"

    Ejemplos negativos (NO son sobre métricas):
    - "¿Cómo está el sentimiento?"
    - "¿Cómo se propagó el post 12345?"
    """
    message_lower = message.lower().strip()

    # Palabras clave que indican pregunta sobre métricas/influencia
    metrics_keywords = [
        "comentado",
        "popular",
        "impacto",
        "influyente",
        "top",
        "quién escribió",
        "quién es el",
        "quién es el usuario",
        "quién es el autor",
        "más activo",
        "más respuestas",
        "más comentarios",
        "más engagement",
        "autor más",
        "usuario más",
        "post más",
        "publicación más",
        "quien fue",
        "quién fue",
    ]

    # Patrones específicos de intención de métricas
    metrics_patterns = [
        r"¿?quién escribió.*(?:post|publicacion|mensaje).*(?:comentado|popular|impacto)",
        r"¿?quién es.*(?:usuario|autor).*(?:influyente|activo|top)",
        r"¿?cuál es.*(?:post|publicacion).*(?:comentado|popular|impacto|respuestas)",
        r"(?:post|publicacion).*más (?:comentado|popular|impacto|respuestas)",
        r"(?:usuario|autor).*más (?:influyente|activo|respuestas)",
        r"top (?:usuarios|autores|posts|publicaciones)",
        r"ranking.*(?:usuario|autor|post)",
        r"más (?:comentado|influyente|popular|impacto|activo)",
    ]

    # Si hay palabra clave de métricas, probablemente es consulta de métricas
    has_metrics_keyword = any(kw in message_lower for kw in metrics_keywords)

    # Si tiene patrón específico, definitivamente es de métricas
    for pattern in metrics_patterns:
        if re.search(pattern, message_lower):
            return True

    # Si tiene palabras clave de métricas, es probablemente de métricas
    if has_metrics_keyword:
        # Filtrar falsos positivos: preguntas sobre propagación o sentimiento
        false_positive_keywords = [
            "propagación",
            "propagacion",
            "propagó",
            "propagation",
            "sentimiento",
            "clima",
            "polaridad"
        ]

        has_false_positive = any(kw in message_lower for kw in false_positive_keywords)
        if not has_false_positive:
            return True

    return False


# ==============================================================================
# INICIALIZAR LLM CON TOOLS (Native Tool Calling + Phase 5 Factory)
# ==============================================================================

llm = create_llm()

# Bind tools natively (no más regex parsing)
llm_with_tools = llm.bind_tools(TOOLS)


# ==============================================================================
# NODOS DEL GRAFO
# ==============================================================================

def node_process_input(state: AgentStateDict) -> AgentStateDict:
    """
    Nodo 1: Procesar entrada del usuario
    - Detectar inyecciones de prompt
    - Detectar PII
    - Preparar contexto para el siguiente nodo
    """
    messages: List[BaseMessage] = state.get("messages", [])

    if not messages:
        return state

    # Obtener último mensaje del usuario
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break

    if not last_user_message:
        return state

    # ===========================================================================
    # SEGURIDAD: DETECCIÓN DE INYECCIONES
    # ===========================================================================

    has_injection = detect_prompt_injection(last_user_message)
    injection_severity = get_injection_severity(last_user_message) if has_injection else "SAFE"

    # Si hay cualquier inyección detectada, bloquear (LOW, MEDIUM, HIGH)
    if has_injection:
        error_msg = f"🔒 Security: Suspicious input detected and blocked [{injection_severity}]. Please rephrase your question."
        state["messages"].append(AIMessage(content=error_msg))
        state["security_block"] = True
        return state

    # Guardar información de seguridad en el estado
    state["security_info"] = {
        "has_injection": has_injection,
        "injection_severity": injection_severity,
    }

    # ===========================================================================
    # SEGURIDAD: DETECCIÓN DE PII
    # ===========================================================================

    pii_found = detect_pii(last_user_message)
    has_pii = any(pii_found.values())

    if has_pii:
        state["security_info"]["pii_detected"] = True
        state["security_info"]["pii_types"] = pii_found
    else:
        state["security_info"]["pii_detected"] = False

    return state


def node_route_to_tool(state: AgentStateDict) -> AgentStateDict:
    """
    Nodo 2: Determinar si necesita una herramienta (Native Tool Calling)

    Lógica mejorada de routing:
    1. Primero detecta intenciones específicas (ej: sentimiento general)
    2. Luego llama al LLM con .bind_tools() para native tool calling

    Retorna:
    - Si usa tool: state actualizado con tool_call
    - Si no usa tool: AIMessage agregado al state
    """
    messages: List[BaseMessage] = state.get("messages", [])

    if not messages:
        return state

    # Obtener último mensaje del usuario
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break

    if not last_user_message:
        return state

    # ===========================================================================
    # DETECCIÓN DE INTENCIONES EXPLÍCITAS
    # ===========================================================================

    # Si detecta pregunta de sentimiento GENERAL, llamar directamente a analyze_sentiment
    if detect_sentiment_intent(last_user_message):
        state["last_tool_result"] = {
            "tool_name": "analyze_sentiment",
            "input": {},
            "is_tool_call": True
        }
        return state

    # Si detecta pregunta de MÉTRICAS/INFLUENCIA, llamar directamente a get_influence_metrics
    if detect_metrics_intent(last_user_message):
        state["last_tool_result"] = {
            "tool_name": "get_influence_metrics",
            "input": {},
            "is_tool_call": True
        }
        return state

    # ===========================================================================
    # ROUTING GENÉRICO CON LLM - NATIVE TOOL CALLING (NO MÁS REGEX)
    # ===========================================================================

    system_prompt = get_route_system_prompt(TOOLS_SCHEMA, len(messages), state.get("current_topic", "general"))

    try:
        # Llamar al LLM CON tools nativas (NO más TOOL_CALL regex)
        response = llm_with_tools.invoke(
            messages[-4:] if len(messages) > 4 else messages,
            system_message=system_prompt
        )

        # ===========================================================================
        # FINOPS: CAPTURAR TOKENS (Phase 2)
        # ===========================================================================
        usage = response.response_metadata.get("token_usage", {}) if hasattr(response, "response_metadata") else {}
        if usage:
            state.setdefault("token_usage", []).append({
                "call": "route",
                "model": config.LLM_MODEL,
                "input": usage.get("prompt_tokens", 0),
                "output": usage.get("completion_tokens", 0),
            })

        # Chequear si hay tool_calls en la respuesta (native format)
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # OpenAI devuelve tool_calls como lista
            tool_call = response.tool_calls[0]
            state["last_tool_result"] = {
                "tool_name": tool_call.get("name") or tool_call.name,
                "input": tool_call.get("args") or tool_call.args,
                "is_tool_call": True
            }
        else:
            # Sin tool call, agregar respuesta directamente
            state["messages"].append(AIMessage(content=response.content))

        return state

    except Exception as e:
        error_msg = f"Error en LLM: {str(e)}"
        state["messages"].append(AIMessage(content=error_msg))
        return state


def node_execute_tool(state: AgentStateDict) -> AgentStateDict:
    """
    Nodo 3: Ejecutar la herramienta seleccionada
    - Si hay is_tool_call=True, ejecutar
    - Sino, pasar al siguiente nodo
    """
    tool_result = state.get("last_tool_result")

    # Solo ejecutar si es un tool call (no es una respuesta sin herramienta)
    if not tool_result or not tool_result.get("is_tool_call", False):
        return state

    try:
        tool_name = tool_result.get("tool_name")
        tool_input = tool_result.get("input", {})

        # Ejecutar herramienta
        result = execute_tool(tool_name, tool_input)

        # Guardar resultado en estado (reemplazar el tool call con el resultado)
        state["last_tool_result"] = {
            "tool_name": tool_name,
            "input": tool_input,
            "result": result,
            "is_tool_call": False  # Ya ejecutado
        }
        state["recent_tool_calls"].append({
            "tool": tool_name,
            "input": tool_input,
            "result": result
        })

        return state

    except Exception as e:
        state["last_tool_result"] = {
            "error": str(e),
            "is_tool_call": False
        }
        return state


def node_generate_response(state: AgentStateDict) -> AgentStateDict:
    """
    Nodo 4: Generar respuesta final
    - Si se ejecutó una tool, usar el resultado
    - Formatear respuesta conversacional
    - Extraer información relevante según el tipo de tool
    """
    messages: List[BaseMessage] = state.get("messages", [])
    tool_result = state.get("last_tool_result")

    if not messages:
        return state

    context = ""
    if tool_result and "error" not in tool_result:
        tool_name = tool_result.get("tool_name")
        result_data = tool_result.get("result", {})

        # Procesar resultado según el tipo de tool
        if tool_name == "get_influence_metrics":
            metrics_summary = {
                "top_autores": result_data.get("top_autores_por_influencia", [])[:3],
                "top_posts": result_data.get("top_posts_comentados", [])[:3],
                "estadisticas": result_data.get("estadisticas_generales", {})
            }
            context = f"\nMetrics Analysis Result:\n{json.dumps(metrics_summary, indent=2, ensure_ascii=False)}"

        elif tool_name == "analyze_sentiment":
            sentiment_summary = {
                "distribucion": result_data.get("distribucion", []),
                "sentimiento_dominante": result_data.get("sentimiento_dominante"),
                "muestras": result_data.get("muestras_por_sentimiento", {})
            }
            context = f"\nSentiment Analysis Result:\n{json.dumps(sentiment_summary, indent=2, ensure_ascii=False)}"

        elif tool_name == "trace_propagation":
            propagation_summary = {
                "alcance_total": result_data.get("alcance_total"),
                "hijos_directos": result_data.get("hijos_directos"),
                "profundidad": result_data.get("profundidad_maxima"),
                "velocidad_media": result_data.get("velocidad_media_minutos"),
                "top_autores": result_data.get("top_autores_respuestas", {})
            }
            context = f"\nPropagation Analysis Result:\n{json.dumps(propagation_summary, indent=2, ensure_ascii=False)}"
        else:
            context = f"\nTool result:\n{json.dumps(tool_result, indent=2, ensure_ascii=False)[:500]}"

    elif tool_result and "error" in tool_result:
        context = f"\nTool error: {tool_result['error']}\n\nRespond to the user explaining that you couldn't retrieve the data, but try to help with what you know."

    # ===========================================================================
    # LONG-TERM MEMORY: PASAR CONTEXTO DE SESIONES PREVIAS (Phase 3)
    # ===========================================================================
    long_term_context = state.get("long_term_context", "")
    system_prompt = get_generate_system_prompt(context, long_term_context=long_term_context)

    try:
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            *[{"role": msg.type, "content": msg.content} for msg in messages[-3:]]
        ])

        # ===========================================================================
        # FINOPS: CAPTURAR TOKENS (Phase 2)
        # ===========================================================================
        usage = response.response_metadata.get("token_usage", {}) if hasattr(response, "response_metadata") else {}
        if usage:
            state.setdefault("token_usage", []).append({
                "call": "generate",
                "model": config.LLM_MODEL,
                "input": usage.get("prompt_tokens", 0),
                "output": usage.get("completion_tokens", 0),
            })

        response_text = response.content

        # ===========================================================================
        # SEGURIDAD: ENMASCARAR PII EN LA RESPUESTA
        # ===========================================================================

        masked_response, _ = mask_sensitive_data(response_text)

        # Si ya no hay respuesta previa, agregarla
        if not any(isinstance(m, AIMessage) for m in messages[-1:]):
            state["messages"].append(AIMessage(content=masked_response))
        else:
            # Reemplazar última respuesta
            state["messages"][-1] = AIMessage(content=masked_response)

    except Exception as e:
        state["messages"].append(AIMessage(content=f"Error: {str(e)}"))

    return state


# ==============================================================================
# NODOS DE PATRONES (Phase 6 - Design Patterns)
# ==============================================================================

def node_react_think(state: AgentStateDict) -> AgentStateDict:
    """
    Nodo ReAct: genera Thought/Action/Observation/Reflection
    Usado cuando pattern_mode == "react"
    """
    messages: List[BaseMessage] = state.get("messages", [])
    if not messages:
        return state

    system_prompt = get_react_system_prompt()

    try:
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            *[{"role": msg.type, "content": msg.content} for msg in messages[-3:]]
        ])

        response_text = response.content

        # Parsear Thought/Action/Observation/Reflection
        react_trace = {
            "thought": _extract_between(response_text, "Thought:", "Action:"),
            "action": _extract_between(response_text, "Action:", "Observation:"),
            "observation": _extract_between(response_text, "Observation:", "Reflection:"),
            "reflection": _extract_between(response_text, "Reflection:", None)
        }

        state["react_trace"] = react_trace

        # Si hay TOOL_CALL en la acción, marcar para ejecutar
        if "TOOL_CALL" in response_text:
            import json
            tool_call_str = _extract_between(response_text, "TOOL_CALL:", None)
            try:
                tool_call = json.loads(tool_call_str)
                state["last_tool_result"] = {
                    "tool_name": tool_call.get("tool_name"),
                    "input": tool_call.get("input", {}),
                    "is_tool_call": True
                }
            except:
                pass

    except Exception as e:
        state["messages"].append(AIMessage(content=f"Error en ReAct: {e}"))

    return state


def node_reflect(state: AgentStateDict) -> AgentStateDict:
    """
    Nodo Reflection: evalúa si la respuesta es suficiente
    Usado cuando pattern_mode == "reflection"
    """
    messages: List[BaseMessage] = state.get("messages", [])
    tool_result = state.get("last_tool_result")

    if not messages or not tool_result:
        return state

    # Obtener la última respuesta del agente y el resultado del tool
    context = f"Tool result: {json.dumps(tool_result.get('result', {}), ensure_ascii=False)[:500]}"
    system_prompt = get_reflection_system_prompt()

    try:
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            *[{"role": msg.type, "content": msg.content} for msg in messages[-3:]],
            {"role": "user", "content": f"User question context: {context}"}
        ])

        response_text = response.content.upper()

        if "SUFFICIENT" in response_text:
            state["reflection_insufficient"] = False
        elif "INSUFFICIENT" in response_text or "AMBIGUOUS" in response_text:
            state["reflection_insufficient"] = True
            state["reflection_retries"] = state.get("reflection_retries", 0) + 1

    except Exception as e:
        state["reflection_insufficient"] = False  # Por defecto, continuar

    return state


def node_plan(state: AgentStateDict) -> AgentStateDict:
    """
    Nodo Planning: descompone query compleja en pasos
    Usado cuando pattern_mode == "planning"
    """
    messages: List[BaseMessage] = state.get("messages", [])
    if not messages:
        return state

    system_prompt = get_planning_system_prompt()

    try:
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            *[{"role": msg.type, "content": msg.content} for msg in messages[-2:]]
        ])

        response_text = response.content

        # Parsear JSON con steps
        import json
        json_str = _extract_between(response_text, "[", "]") or response_text
        try:
            steps = json.loads("[" + json_str + "]" if "[" not in json_str else json_str)
            state["plan_steps"] = steps
            state["plan_current_step"] = 0

            # Mostrar el plan al usuario
            plan_msg = f"[Planning] Plan generado con {len(steps)} pasos:\n"
            for step in steps:
                plan_msg += f"  {step.get('step')}: {step.get('task')} (tool: {step.get('tool')})\n"

            state["messages"].append(AIMessage(content=plan_msg))
        except:
            state["plan_steps"] = []

    except Exception as e:
        state["messages"].append(AIMessage(content=f"Error en Planning: {e}"))

    return state


def node_hitl_check(state: AgentStateDict) -> AgentStateDict:
    """
    Nodo HITL: pausa para confirmación del usuario antes de ejecutar tool
    Usado cuando pattern_mode == "hitl"
    """
    tool_result = state.get("last_tool_result")

    if not tool_result or not tool_result.get("is_tool_call"):
        return state

    tool_name = tool_result.get("tool_name")
    tool_input = tool_result.get("input", {})

    # Generar mensaje de confirmación
    approval_msg = f"[HITL_PENDING] ¿Ejecutar {tool_name} con parámetros {tool_input}? (responde 'si' o 'no')"

    state["messages"].append(AIMessage(content=approval_msg))
    state["hitl_pending"] = True

    return state


# ==============================================================================
# FUNCIONES DE ROUTING (Conditional Edges)
# ==============================================================================

def route_after_input(state: AgentStateDict) -> str:
    """Decidir si ir a Planning o Route-to-Tool"""
    mode = state.get("pattern_mode")
    messages = state.get("messages", [])

    if mode == "planning" and len(messages) > 0:
        # Detectar si la query es compleja (multiple preguntas, "y")
        last_msg = messages[-1].content if isinstance(messages[-1], HumanMessage) else ""
        if " y " in last_msg.lower() or "?" in last_msg.count("?") > 1:
            return "node_plan"

    return "route_to_tool"


def route_after_tool_selection(state: AgentStateDict) -> str:
    """Decidir si ir a ReAct, HITL, Execute, o Generate"""
    mode = state.get("pattern_mode")
    tool_result = state.get("last_tool_result")
    has_tool = bool(tool_result and tool_result.get("is_tool_call"))

    if not has_tool:
        return "generate_response"

    if mode == "react":
        return "node_react_think"
    elif mode == "hitl":
        return "node_hitl_check"
    else:
        return "execute_tool"


def route_after_execute(state: AgentStateDict) -> str:
    """Decidir si ir a Reflection o Generate"""
    mode = state.get("pattern_mode")

    if mode == "reflection":
        return "node_reflect"
    else:
        return "generate_response"


def route_after_reflect(state: AgentStateDict) -> str:
    """Decidir si retornar a Route (retry) o Generate"""
    insufficient = state.get("reflection_insufficient", False)
    retries = state.get("reflection_retries", 0)

    if insufficient and retries < 1:
        return "route_to_tool"
    else:
        return "generate_response"


# ==============================================================================
# UTILIDADES
# ==============================================================================

def _extract_between(text: str, start: str, end: str) -> str:
    """Extraer substring entre dos delimitadores"""
    try:
        if start not in text:
            return ""
        start_idx = text.find(start) + len(start)
        if end is None:
            return text[start_idx:].strip()
        end_idx = text.find(end, start_idx)
        if end_idx == -1:
            return text[start_idx:].strip()
        return text[start_idx:end_idx].strip()
    except:
        return ""


# ==============================================================================
# CONSTRUIR GRAFO
# ==============================================================================

def build_agent_graph() -> StateGraph:
    """
    Construir el grafo LangGraph del agente

    Flujo:
    1. input -> procesar usuario
    2. route -> decidir tool
    3. execute -> ejecutar tool (si aplica)
    4. response -> generar respuesta
    5. end
    """
    graph = StateGraph(AgentStateDict)

    # Agregar nodos (existentes)
    graph.add_node("process_input", node_process_input)
    graph.add_node("route_to_tool", node_route_to_tool)
    graph.add_node("execute_tool", node_execute_tool)
    graph.add_node("generate_response", node_generate_response)

    # Agregar nodos (nuevos - Phase 6)
    graph.add_node("node_react_think", node_react_think)
    graph.add_node("node_reflect", node_reflect)
    graph.add_node("node_plan", node_plan)
    graph.add_node("node_hitl_check", node_hitl_check)

    # Definir conditional edges
    # process_input → (planning | route_to_tool)
    graph.add_conditional_edges(
        "process_input",
        route_after_input,
        {"node_plan": "node_plan", "route_to_tool": "route_to_tool"}
    )

    # node_plan → route_to_tool
    graph.add_edge("node_plan", "route_to_tool")

    # route_to_tool → (node_react_think | node_hitl_check | execute_tool | generate_response)
    graph.add_conditional_edges(
        "route_to_tool",
        route_after_tool_selection,
        {
            "node_react_think": "node_react_think",
            "node_hitl_check": "node_hitl_check",
            "execute_tool": "execute_tool",
            "generate_response": "generate_response"
        }
    )

    # node_react_think → execute_tool
    graph.add_edge("node_react_think", "execute_tool")

    # node_hitl_check → END (pausa para confirmación)
    graph.add_edge("node_hitl_check", END)

    # execute_tool → (node_reflect | generate_response)
    graph.add_conditional_edges(
        "execute_tool",
        route_after_execute,
        {"node_reflect": "node_reflect", "generate_response": "generate_response"}
    )

    # node_reflect → (route_to_tool | generate_response)
    graph.add_conditional_edges(
        "node_reflect",
        route_after_reflect,
        {"route_to_tool": "route_to_tool", "generate_response": "generate_response"}
    )

    # generate_response → END
    graph.add_edge("generate_response", END)

    # Establecer entry point
    graph.set_entry_point("process_input")

    # Compilar
    compiled_graph = graph.compile()

    return compiled_graph


# ==============================================================================
# AGENTE WRAPPER
# ==============================================================================

class ConversationalAgent:
    """Wrapper del agente que maneja la memoria, seguridad e interacción"""

    def __init__(self, session_id: str = None, user_id: str = None):
        self.graph = build_agent_graph()
        self.memory = ConversationalMemory(max_messages=6)
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id or "anonymous"

        # Componentes de seguridad
        self.audit_logger = AuditLogger() if config.SECURITY_AUDIT_ENABLED else None
        self.rate_limiter = RateLimiter(max_requests=20, time_window=60) if config.SECURITY_RATE_LIMITING_ENABLED else None

        # Componentes de FinOps (Phase 2)
        self.cost_tracker = CostTracker(
            default_model=config.LLM_MODEL,
            monthly_queries_estimate=config.FINOPS_MONTHLY_QUERIES_ESTIMATE
        ) if config.FINOPS_ENABLED else None
        self.last_query_tokens = {"input": 0, "output": 0, "total": 0}

        # Componentes de Long-Term Memory (Phase 3)
        try:
            self.long_term_memory = create_memory_backend(config.LT_MEMORY_BACKEND) if config.LT_MEMORY_ENABLED else None
        except Exception as e:
            print(f"[Warning] Long-Term Memory initialization failed: {e}. Running without LTM.")
            self.long_term_memory = None

        # Componentes de Observability (Phase 4)
        self.tracer = LocalTracer() if config.OBS_ENABLED else None
        self.ragas_eval = RagasEvaluator(llm=llm) if config.OBS_RAGAS_ENABLED else None
        self.last_eval_result = None

        # Cargar usernames del dataset para detección de PII
        try:
            from shared.data_loader import get_loader
            loader = get_loader()
            load_usernames_from_loader(loader)
        except Exception as e:
            print(f"Warning: Could not load usernames for PII detection: {e}")

        self.state: AgentStateDict = {
            "messages": [],
            "last_tool_result": None,
            "current_topic": None,
            "recent_tool_calls": [],
            "react_trace": None,  # Para ReAct pattern (Fase 1.6)
            "pattern_mode": None,  # Patrón activo: "react" | "reflection" | "planning" | "hitl" | "crew" | None
            "security_info": {},  # Información de seguridad
            "token_usage": [],  # Rastreo de tokens (Phase 2)
            # Phase 6: Design Patterns
            "hitl_pending": False,
            "hitl_approved": False,
            "reflection_insufficient": False,
            "reflection_retries": 0,
            "plan_steps": [],
            "plan_current_step": 0,
        }

    def chat(self, user_message: str) -> str:
        """
        Procesar un mensaje del usuario y retornar respuesta
        Incluye seguridad, rate limiting y auditoría

        Args:
            user_message: Mensaje del usuario

        Returns:
            Respuesta del agente
        """
        # ===========================================================================
        # SEGURIDAD: RATE LIMITING
        # ===========================================================================

        if self.rate_limiter:
            allowed, reason = self.rate_limiter.is_allowed(self.user_id)
            if not allowed:
                return f"Access denied: {reason}"

        # ===========================================================================
        # LONG-TERM MEMORY: RECUPERAR CONTEXTO DE SESIONES PREVIAS (Phase 3)
        # ===========================================================================

        if self.long_term_memory:
            try:
                relevant = self.long_term_memory.search_relevant(
                    query=user_message,
                    top_k=config.LT_MEMORY_TOP_K,
                    exclude_session=self.session_id
                )

                if relevant:
                    # Formatear memories para inyectar en el grafo
                    context_parts = []
                    for entry in relevant[:config.LT_MEMORY_TOP_K]:
                        # Simplificar para no sobrecargar el contexto
                        context_parts.append(f"Q: {entry.user_msg[:100]}...\nA: {entry.agent_msg[:100]}...")

                    self.state["long_term_context"] = "\n---\n".join(context_parts)
                else:
                    self.state["long_term_context"] = None
            except Exception as e:
                print(f"[Warning] Long-term memory search failed: {e}")
                self.state["long_term_context"] = None

        # ===========================================================================
        # OBSERVABILITY: INICIAR TRAZA (Phase 4)
        # ===========================================================================

        query_id = self.tracer.start_query(user_message) if self.tracer else None
        self.state["query_id"] = query_id

        # Agregar mensaje a estado
        self.memory.add_user_message(user_message)
        self.state["messages"] = self.memory.get_messages()

        # Ejecutar grafo
        output = self.graph.invoke(self.state)

        # Actualizar estado
        self.state = output

        # ===========================================================================
        # FINOPS: PROCESAR TOKENS (Phase 2)
        # ===========================================================================

        if self.cost_tracker:
            # Obtener tokens nuevos capturados en esta query
            prev_token_count = len(self.state.get("token_usage", []) or [])
            new_calls = output.get("token_usage", [])[prev_token_count:]

            # Registrar en cost tracker
            for call in new_calls:
                self.cost_tracker.record(
                    call_name=call["call"],
                    model=call["model"],
                    input_tokens=call["input"],
                    output_tokens=call["output"]
                )

            # Actualizar último query tokens
            query_in = sum(c["input"] for c in new_calls)
            query_out = sum(c["output"] for c in new_calls)
            self.last_query_tokens = {
                "input": query_in,
                "output": query_out,
                "total": query_in + query_out
            }

        # ===========================================================================
        # SEGURIDAD: AUDITORÍA
        # ===========================================================================

        if self.audit_logger:
            security_info = output.get("security_info", {})
            has_injection = security_info.get("has_injection", False)
            injection_severity = security_info.get("injection_severity", "SAFE")
            pii_detected = security_info.get("pii_detected", False)
            pii_types = json.dumps(security_info.get("pii_types", {}))

            # Registrar rate limiting
            if self.rate_limiter:
                self.rate_limiter.record(self.user_id, is_injection=has_injection)

        # Obtener última respuesta del asistente
        tool_called = None
        _latency = 0.0  # Para dashboard (scoping)
        for msg in reversed(output["messages"]):
            if isinstance(msg, AIMessage):
                response_text = msg.content

                # Registrar en auditoría
                if self.audit_logger:
                    self.audit_logger.log(
                        session_id=self.session_id,
                        user_id=self.user_id,
                        query=user_message,
                        response=response_text,
                        tool_called=tool_called,
                        has_injection=has_injection,
                        injection_severity=injection_severity,
                        pii_detected=pii_detected,
                        pii_types=pii_types if pii_detected else None,
                    )

                # ===========================================================================
                # LONG-TERM MEMORY: GUARDAR TURNO EN BASE DE DATOS (Phase 3)
                # ===========================================================================

                if self.long_term_memory:
                    try:
                        self.long_term_memory.save_turn(
                            session_id=self.session_id,
                            user_msg=user_message,
                            agent_msg=response_text,
                            metadata={"topic": self.state.get("current_topic", "general")}
                        )
                    except Exception as e:
                        print(f"[Warning] Long-term memory save failed: {e}")

                # ===========================================================================
                # OBSERVABILITY: FINALIZAR TRAZA Y EVALUAR (Phase 4)
                # ===========================================================================

                if self.tracer and query_id:
                    # Obtener tokens de la última query
                    last_tokens = self.last_query_tokens if self.cost_tracker else {"input": 0, "output": 0}
                    # Obtener tool llamada
                    tool_called = output.get("last_tool_result", {}).get("tool_name") if output.get("last_tool_result") else None
                    # Finalizar traza y obtener latencia
                    _latency = self.tracer.end_query(
                        query_id=query_id,
                        tool_called=tool_called,
                        input_tokens=last_tokens.get("input", 0),
                        output_tokens=last_tokens.get("output", 0),
                        success=True
                    )
                    print(f"[Trace] Latency: {_latency:.0f}ms | Tool: {tool_called or 'none'}")

                # Ragas evaluation
                if self.ragas_eval:
                    try:
                        tool_context = json.dumps(output.get("last_tool_result", {}) or {})[:300]
                        eval_result = self.ragas_eval.evaluate(user_message, response_text, tool_context)
                        self.last_eval_result = eval_result
                        if eval_result.ragas_available:
                            print(f"[Ragas] Relevancy: {eval_result.answer_relevancy:.2f} | Faithfulness: {eval_result.faithfulness:.2f}")
                        else:
                            print(f"[Ragas] (Fallback LLM) Relevancy: {eval_result.answer_relevancy:.2f}")
                    except Exception as e:
                        print(f"[Warning] Ragas evaluation failed: {e}")

                self.memory.add_assistant_message(response_text)

                # ===========================================================================
                # DASHBOARD: PERSISTIR MÉTRICAS PARA STREAMLIT (Diferenciador)
                # ===========================================================================

                try:
                    from dashboard.metrics_store import append_metric
                    append_metric({
                        "query_id": query_id or "unknown",
                        "timestamp": datetime.now().isoformat(),
                        "session_id": self.session_id,
                        "latency_ms": _latency,
                        "tool_called": tool_called,
                        "input_tokens": self.last_query_tokens.get("input", 0),
                        "output_tokens": self.last_query_tokens.get("output", 0),
                        "total_tokens": self.last_query_tokens.get("total", 0),
                        "total_cost": self.cost_tracker.get_query_cost(
                            self.last_query_tokens.get("input", 0),
                            self.last_query_tokens.get("output", 0)
                        ) if self.cost_tracker else 0.0,
                        "session_cost_cumulative": self.cost_tracker.session_cost if self.cost_tracker else 0.0,
                        "answer_relevancy": self.last_eval_result.answer_relevancy if self.last_eval_result else None,
                        "faithfulness": self.last_eval_result.faithfulness if self.last_eval_result else None,
                        "success": True,
                    })
                except Exception:
                    # Nunca crashear el agente por culpa de métricas del dashboard
                    pass

                return response_text

        return "No response generated"

    def reset(self):
        """Resetear la conversación"""
        self.memory.clear()
        if self.cost_tracker:
            self.cost_tracker.reset()
        if self.tracer:
            self.tracer.reset()
        if self.ragas_eval:
            self.ragas_eval.reset()
        self.state = {
            "messages": [],
            "last_tool_result": None,
            "current_topic": None,
            "recent_tool_calls": [],
            "react_trace": None,
            "pattern_mode": None,
            "token_usage": [],
            "long_term_context": None,
            "query_id": None,
            # Phase 6: Design Patterns
            "hitl_pending": False,
            "hitl_approved": False,
            "reflection_insufficient": False,
            "reflection_retries": 0,
            "plan_steps": [],
            "plan_current_step": 0,
        }

    def set_pattern_mode(self, mode: str) -> None:
        """
        Establecer el patrón de ejecución del agente

        Args:
            mode: "react" | "reflection" | "planning" | "hitl" | "crew" | None
        """
        if mode and mode not in ["react", "reflection", "planning", "hitl", "crew"]:
            print(f"[WARNING] Unknown pattern mode: {mode}. Use: react, reflection, planning, hitl, crew, or None")
            return
        self.state["pattern_mode"] = mode
        mode_name = mode if mode else "default"
        print(f"[Pattern] Pattern mode set to: {mode_name}")

    def get_conversation_history(self) -> str:
        """Obtener historial de conversación"""
        return self.memory.get_context_for_prompt()

    def get_security_report(self) -> Dict[str, Any]:
        """Obtener reporte de seguridad de la sesión actual"""
        if not self.audit_logger:
            return {"error": "Audit logging not enabled"}

        session_summary = self.audit_logger.get_session_summary(self.session_id)
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "session_summary": session_summary,
        }

    def export_audit_logs(self, output_file: str = None) -> str:
        """Exportar logs de auditoría de la sesión"""
        if not self.audit_logger:
            return json.dumps({"error": "Audit logging not enabled"})

        return self.audit_logger.export_logs(session_id=self.session_id, output_file=output_file)

    def get_cost_report(self) -> str:
        """
        Obtener reporte de costos de la sesión (Phase 2 FinOps)

        Returns:
            String con reporte formateado
        """
        if not self.cost_tracker:
            return "FinOps tracking not enabled"
        return self.cost_tracker.get_session_report()

    def get_memory_stats(self) -> str:
        """
        Obtener estadísticas de memoria long-term (Phase 3)

        Returns:
            String con estadísticas formateadas
        """
        if not self.long_term_memory:
            return "Long-Term Memory not enabled"

        try:
            stats = self.long_term_memory.get_stats()
            backend_type = stats.get("backend_type", "unknown")

            if backend_type == "sqlite":
                return f"""
Long-Term Memory Statistics (SQLite)
=====================================
Total turns saved:   {stats.get('total_turns', 0)}
Total sessions:      {stats.get('total_sessions', 0)}
Database size:       {stats.get('db_size_mb', 0)} MB
Oldest entry:        {stats.get('oldest_entry', 'N/A')}
Newest entry:        {stats.get('newest_entry', 'N/A')}
DB path:             {stats.get('db_path', 'N/A')}
"""
            elif backend_type == "chroma":
                return f"""
Long-Term Memory Statistics (ChromaDB)
========================================
Total turns saved:   {stats.get('total_turns', 0)}
Total sessions:      {stats.get('total_sessions', 0)}
Directory size:      {stats.get('persist_dir_mb', 0)} MB
Oldest entry:        {stats.get('oldest_entry', 'N/A')}
Newest entry:        {stats.get('newest_entry', 'N/A')}
Persist directory:   {stats.get('persist_dir', 'N/A')}
"""
            elif backend_type == "hybrid":
                sqlite_stats = stats.get("sqlite", {})
                chroma_stats = stats.get("chroma", {})
                return f"""
Long-Term Memory Statistics (Hybrid: SQLite + ChromaDB)
=========================================================
SQLite:
  Total turns:       {sqlite_stats.get('total_turns', 0)}
  Total sessions:    {sqlite_stats.get('total_sessions', 0)}
  Size:              {sqlite_stats.get('db_size_mb', 0)} MB

ChromaDB:
  Total turns:       {chroma_stats.get('total_turns', 0) if isinstance(chroma_stats, dict) else 'N/A'}
  Status:            {'Ready' if isinstance(chroma_stats, dict) else 'Not available'}
"""
            else:
                return str(stats)

        except Exception as e:
            return f"Error getting memory stats: {e}"

    def clear_long_term_memory(self, session_only: bool = True) -> str:
        """
        Limpiar memoria long-term

        Args:
            session_only: Si True, solo limpia la sesión actual. Si False, limpia todo (DESTRUCTIVO)

        Returns:
            Mensaje de confirmación
        """
        if not self.long_term_memory:
            return "Long-Term Memory not enabled"

        try:
            if session_only:
                self.long_term_memory.clear_session(self.session_id)
                return f"Cleared memory for session {self.session_id}"
            else:
                self.long_term_memory.clear_all()
                return "Cleared ALL long-term memory (DESTRUCTIVE OPERATION)"

        except Exception as e:
            return f"Error clearing memory: {e}"

    def get_metrics_report(self) -> str:
        """
        Obtener reporte de métricas de observabilidad (Phase 4)

        Returns:
            String con reporte formateado
        """
        if not self.tracer:
            return "Observability tracing not enabled"
        return self.tracer.get_metrics_report()

    def get_eval_report(self) -> str:
        """
        Obtener reporte de evaluación de calidad (Phase 4)

        Returns:
            String con reporte formateado
        """
        if not self.ragas_eval:
            return "Ragas evaluation not enabled"
        return self.ragas_eval.get_eval_report()
