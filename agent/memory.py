"""
Conversational Memory Manager
Gestiona el historial de conversacion con sliding window
"""

from typing import List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage


class ConversationalMemory:
    """
    Memoria conversacional con sliding window

    Mantiene los ultimos N turnos para:
    - Contexto en preguntas de seguimiento
    - Reducir tamanio de prompt
    - Mantener coherencia de conversacion
    """

    def __init__(self, max_messages: int = 6):
        """
        Args:
            max_messages: Numero maximo de mensajes a mantener
        """
        self.max_messages = max_messages
        self.messages: List[BaseMessage] = []

    def add_user_message(self, content: str):
        """Agregar mensaje del usuario"""
        self.messages.append(HumanMessage(content=content))
        self._trim_to_window()

    def add_assistant_message(self, content: str):
        """Agregar mensaje del asistente"""
        self.messages.append(AIMessage(content=content))
        self._trim_to_window()

    def add_tool_result(self, tool_name: str, result: str):
        """
        Agregar resultado de una tool call

        Formato: [Tool: tool_name] result_content
        """
        content = f"[Tool: {tool_name}]\n{result}"
        self.messages.append(AIMessage(content=content))
        self._trim_to_window()

    def get_messages(self) -> List[BaseMessage]:
        """Obtener todos los mensajes en memoria"""
        return self.messages.copy()

    def get_recent_messages(self, limit: Optional[int] = None) -> List[BaseMessage]:
        """
        Obtener ultimos N mensajes

        Args:
            limit: Si None, usa max_messages

        Returns:
            Lista de mensajes recientes
        """
        limit = limit or self.max_messages
        return self.messages[-limit:]

    def clear(self):
        """Limpiar toda la memoria"""
        self.messages.clear()

    def get_context_for_prompt(self) -> str:
        """
        Obtener el contexto como string para pasar al LLM

        Formato:
        User: ...
        Assistant: ...
        User: ...
        Assistant: ...
        """
        context_lines = []

        for msg in self.messages:
            if isinstance(msg, HumanMessage):
                context_lines.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                context_lines.append(f"Assistant: {msg.content}")

        return "\n".join(context_lines)

    def _trim_to_window(self):
        """Mantener solo los ultimos max_messages"""
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def __repr__(self) -> str:
        return f"ConversationalMemory(messages={len(self.messages)}, max={self.max_messages})"

    def __len__(self) -> int:
        return len(self.messages)
