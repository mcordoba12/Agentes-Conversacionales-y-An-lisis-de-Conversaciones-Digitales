"""
Agent State Definition for LangGraph
Define la estructura del estado compartido del grafo
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage


@dataclass
class AgentState:
    """
    Estado del agente conversacional

    Se pasa entre nodos del grafo LangGraph
    """

    # Historial de mensajes (memoria)
    messages: List[BaseMessage] = field(default_factory=list)

    # Ultimo resultado de una llamada a tool
    last_tool_result: Optional[Dict[str, Any]] = None

    # Tema o contexto actual
    current_topic: Optional[str] = None

    # Ultimas llamadas a tools (para contexto)
    recent_tool_calls: List[Dict[str, Any]] = field(default_factory=list)

    def add_message(self, message: BaseMessage):
        """Agregar un mensaje al historial"""
        self.messages.append(message)

    def add_human_message(self, content: str):
        """Agregar mensaje del usuario"""
        self.add_message(HumanMessage(content=content))

    def add_ai_message(self, content: str):
        """Agregar mensaje del agente"""
        self.add_message(AIMessage(content=content))

    def get_recent_messages(self, limit: int = 6) -> List[BaseMessage]:
        """
        Obtener los ultimos N mensajes (sliding window)
        Util para limitar el contexto enviado al LLM
        """
        return self.messages[-limit:]

    def set_topic(self, topic: str):
        """Establecer el tema actual (tracking)"""
        self.current_topic = topic

    def get_context_str(self) -> str:
        """Obtener el contexto actual como string"""
        context = []

        if self.current_topic:
            context.append(f"Current topic: {self.current_topic}")

        if self.last_tool_result:
            context.append(f"Last result: {self.last_tool_result}")

        return "\n".join(context) if context else ""


# Usar TypedDict alternativo para compatibilidad con LangGraph
from typing import TypedDict

class AgentStateDict(TypedDict, total=False):
    """Estado como TypedDict para LangGraph StateGraph"""
    messages: List[BaseMessage]
    last_tool_result: Optional[Dict[str, Any]]
    current_topic: Optional[str]
    recent_tool_calls: List[Dict[str, Any]]

    # Nuevos campos para Phase 1+ (prompts, patterns)
    react_trace: Optional[Dict[str, str]]        # {"thought": str, "action": str, "observation": str, "reflection": str}
    pattern_mode: Optional[str]                  # "react" | "reflection" | "planning" | "hitl" | "crew" | None

    # Campos para Phase 6 (patterns) - ahora usados en Fase 6
    hitl_pending: Optional[bool]
    hitl_approved: Optional[bool]
    reflection_insufficient: Optional[bool]
    reflection_retries: Optional[int]
    plan_steps: Optional[List[Dict[str, Any]]]
    plan_current_step: Optional[int]

    # Campos para Phase 2 (FinOps)
    token_usage: Optional[List[Dict[str, Any]]]  # Lista de registros de tokens por llamada LLM
    security_info: Optional[Dict[str, Any]]      # Información de seguridad (inyecciones, PII, etc)

    # Campos para Phase 3 (Long-Term Memory)
    long_term_context: Optional[str]             # Contexto recuperado de sesiones previas

    # Campos para Phase 4 (Observability)
    query_id: Optional[str]                      # ID de query para correlacionar con trazas
