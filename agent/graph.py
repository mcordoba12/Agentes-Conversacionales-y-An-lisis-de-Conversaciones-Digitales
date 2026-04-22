"""
LangGraph State Graph for Conversational Agent
Define el flujo del agente y la orquestacion de tools
"""

import json
import re
from typing import Dict, Any, List, Union

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from .state import AgentStateDict
from .memory import ConversationalMemory
from .tools import execute_tool, TOOLS_SCHEMA
import config


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
# INICIALIZAR LLM
# ==============================================================================

llm = ChatOpenAI(
    model=config.LLM_MODEL,
    temperature=config.LLM_TEMPERATURE,
    api_key=config.OPENAI_API_KEY
)


# ==============================================================================
# NODOS DEL GRAFO
# ==============================================================================

def node_process_input(state: AgentStateDict) -> AgentStateDict:
    """
    Nodo 1: Procesar entrada del usuario
    - Agregar mensaje a memoria
    - Preparar contexto
    """
    # El mensaje ya esta en state["messages"]
    # Solo preparamos el estado para el siguiente nodo
    return state


def node_route_to_tool(state: AgentStateDict) -> AgentStateDict:
    """
    Nodo 2: Determinar si necesita una herramienta

    Lógica mejorada de routing:
    1. Primero detecta intenciones específicas (ej: sentimiento general)
    2. Luego llama al LLM para routing genérico

    Retorna:
    - Si usa tool: state actualizado
    - Si no usa tool: ir a response_generator
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
            "input": {}  # Sin parámetros - análisis global
        }
        return state

    # Si detecta pregunta de MÉTRICAS/INFLUENCIA, llamar directamente a get_influence_metrics
    if detect_metrics_intent(last_user_message):
        state["last_tool_result"] = {
            "tool_name": "get_influence_metrics",
            "input": {}  # Sin parámetros - análisis global de métricas
        }
        return state

    # ===========================================================================
    # ROUTING GENÉRICO CON LLM
    # ===========================================================================

    # Construir prompt del sistema con reglas explícitas
    system_prompt = f"""You are a helpful conversational agent that analyzes digital conversations.

Available tools:
{json.dumps(TOOLS_SCHEMA, indent=2)}

ROUTING RULES - Sigue estas reglas ESTRICTAMENTE:

1. **SENTIMENT ANALYSIS RULES**:
   - Si el usuario pregunta por sentimiento general (sin texto específico) → NUNCA llames herramienta, debería haberlo hecho antes
   - Si el usuario proporciona un texto específico → responde sin herramienta (no tienes API para analizar textos específicos)
   - Ejemplo: "¿Cómo está el sentimiento?" → Ya procesado antes
   - Ejemplo: "¿Sentimiento de este texto?" → Responde conversacionalmente

2. **PROPAGATION RULES**:
   - Requiere post_id específico
   - Si el usuario proporciona un ID → llama trace_propagation
   - Si no hay ID → pide al usuario el ID del post

3. **INFLUENCE RULES**:
   - No requiere parámetros
   - Llama get_influence_metrics solo si el usuario pregunta por influencia, métricas, autores, posts populares

4. **DEFAULT**:
   - Si no necesita herramienta → responde directamente
   - Siempre responde en Spanish

When calling a tool, format it as:
TOOL_CALL: {{"tool_name": "...", "input": {{...}}}}

Current context:
- Recent messages: {len(messages)} messages in history
- Current topic: {state.get('current_topic', 'general')}"""

    try:
        # Llamar al LLM con tool definitions
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            *[{"role": msg.type, "content": msg.content} for msg in messages[-4:]]
        ])

        response_text = response.content

        # Detectar si hay un tool call
        tool_call_match = re.search(r'TOOL_CALL:\s*(\{.*?\})', response_text, re.DOTALL)

        if tool_call_match:
            try:
                tool_call = json.loads(tool_call_match.group(1))
                state["last_tool_result"] = {
                    "tool_name": tool_call.get("tool_name"),
                    "input": tool_call.get("input")
                }
            except json.JSONDecodeError:
                # Si falla el parsing, ir a response sin tool
                state["messages"].append(AIMessage(content=response_text))
        else:
            # Sin tool call, agregar respuesta directamente
            state["messages"].append(AIMessage(content=response_text))

        return state

    except Exception as e:
        error_msg = f"Error en LLM: {str(e)}"
        state["messages"].append(AIMessage(content=error_msg))
        return state


def node_execute_tool(state: AgentStateDict) -> AgentStateDict:
    """
    Nodo 3: Ejecutar la herramienta seleccionada
    - Si hay tool_result, ejecutar
    - Sino, pasar al siguiente
    """
    tool_result = state.get("last_tool_result")

    if not tool_result:
        return state

    try:
        tool_name = tool_result.get("tool_name")
        tool_input = tool_result.get("input", {})

        # Ejecutar herramienta
        result = execute_tool(tool_name, tool_input)

        # Guardar resultado en estado
        state["last_tool_result"] = result
        state["recent_tool_calls"].append({
            "tool": tool_name,
            "input": tool_input,
            "result": result
        })

        return state

    except Exception as e:
        state["last_tool_result"] = {"error": str(e)}
        return state


def node_generate_response(state: AgentStateDict) -> AgentStateDict:
    """
    Nodo 4: Generar respuesta final
    - Si se ejecuto una tool, usar el resultado
    - Formatear respuesta conversacional
    - Extraer información relevante según el tipo de tool
    """
    messages: List[BaseMessage] = state.get("messages", [])
    tool_result = state.get("last_tool_result")

    if not messages:
        return state

    system_prompt = """You are a helpful conversational agent analyzing digital conversations.

Your role is to:
1. Answer questions about conversation data
2. Use tool results to provide insights
3. Extract the MOST RELEVANT information (not all data)
4. Be concise and clear
5. Always respond in Spanish

IMPORTANT:
- If you have metrics data (top authors, top posts), extract the TOP 3-5 items
- Avoid dumping entire JSON structures
- Format as natural conversation, not raw data
- Always cite the data you're using"""

    context = ""
    if tool_result and "error" not in tool_result:
        tool_name = tool_result.get("tool_name")

        # Procesar resultado según el tipo de tool
        if tool_name == "get_influence_metrics":
            # Extraer información relevante de métricas
            result_data = tool_result.get("result", {})

            # Construir resumen de métricas
            metrics_summary = {
                "top_autores": result_data.get("top_autores_por_influencia", [])[:3],
                "top_posts": result_data.get("top_posts_comentados", [])[:3],
                "estadisticas": result_data.get("estadisticas_generales", {})
            }

            context = f"\nMetrics Analysis Result:\n{json.dumps(metrics_summary, indent=2, ensure_ascii=False)}"

        elif tool_name == "analyze_sentiment":
            # Extraer información relevante de sentimientos
            result_data = tool_result.get("result", {})

            sentiment_summary = {
                "distribucion": result_data.get("distribucion", []),
                "sentimiento_dominante": result_data.get("sentimiento_dominante"),
                "muestras": result_data.get("muestras_por_sentimiento", {})
            }

            context = f"\nSentiment Analysis Result:\n{json.dumps(sentiment_summary, indent=2, ensure_ascii=False)}"

        elif tool_name == "trace_propagation":
            # Extraer información relevante de propagación
            result_data = tool_result.get("result", {})

            propagation_summary = {
                "alcance_total": result_data.get("alcance_total"),
                "hijos_directos": result_data.get("hijos_directos"),
                "profundidad": result_data.get("profundidad_maxima"),
                "velocidad_media": result_data.get("velocidad_media_minutos"),
                "top_autores": result_data.get("top_autores_respuestas", {})
            }

            context = f"\nPropagation Analysis Result:\n{json.dumps(propagation_summary, indent=2, ensure_ascii=False)}"
        else:
            # Fallback para otras tools
            context = f"\nTool result:\n{json.dumps(tool_result, indent=2, ensure_ascii=False)[:500]}"

    elif tool_result and "error" in tool_result:
        context = f"\nTool error: {tool_result['error']}\n\nRespond to the user explaining that you couldn't retrieve the data, but try to help with what you know."

    try:
        response = llm.invoke([
            {"role": "system", "content": system_prompt + context},
            *[{"role": msg.type, "content": msg.content} for msg in messages[-3:]]
        ])

        # Si ya no hay respuesta previa, agregarla
        if not any(isinstance(m, AIMessage) for m in messages[-1:]):
            state["messages"].append(AIMessage(content=response.content))
        else:
            # Reemplazar ultima respuesta
            state["messages"][-1] = AIMessage(content=response.content)

    except Exception as e:
        state["messages"].append(AIMessage(content=f"Error: {str(e)}"))

    return state


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

    # Agregar nodos
    graph.add_node("process_input", node_process_input)
    graph.add_node("route_to_tool", node_route_to_tool)
    graph.add_node("execute_tool", node_execute_tool)
    graph.add_node("generate_response", node_generate_response)

    # Definir edges
    graph.add_edge("process_input", "route_to_tool")
    graph.add_edge("route_to_tool", "execute_tool")
    graph.add_edge("execute_tool", "generate_response")
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
    """Wrapper del agente que maneja la memoria y la interaccion"""

    def __init__(self):
        self.graph = build_agent_graph()
        self.memory = ConversationalMemory(max_messages=6)
        self.state: AgentStateDict = {
            "messages": [],
            "last_tool_result": None,
            "current_topic": None,
            "recent_tool_calls": []
        }

    def chat(self, user_message: str) -> str:
        """
        Procesar un mensaje del usuario y retornar respuesta

        Args:
            user_message: Mensaje del usuario

        Returns:
            Respuesta del agente
        """
        # Agregar mensaje a estado
        self.memory.add_user_message(user_message)
        self.state["messages"] = self.memory.get_messages()

        # Ejecutar grafo
        output = self.graph.invoke(self.state)

        # Actualizar estado
        self.state = output

        # Obtener ultima respuesta del asistente
        for msg in reversed(output["messages"]):
            if isinstance(msg, AIMessage):
                self.memory.add_assistant_message(msg.content)
                return msg.content

        return "No response generated"

    def reset(self):
        """Resetear la conversacion"""
        self.memory.clear()
        self.state = {
            "messages": [],
            "last_tool_result": None,
            "current_topic": None,
            "recent_tool_calls": []
        }

    def get_conversation_history(self) -> str:
        """Obtener historial de conversacion"""
        return self.memory.get_context_for_prompt()
