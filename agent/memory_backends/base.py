"""
Base class and interfaces for Long-Term Memory backends
Abstracción para persistencia entre sesiones (SQLite, ChromaDB, Hybrid)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class MemoryEntry:
    """
    Una entrada en la memoria long-term

    Representa un turno de conversación guardado
    """
    session_id: str
    user_msg: str
    agent_msg: str
    timestamp: str
    topic: Optional[str] = None
    relevance_score: float = 0.0

    def __post_init__(self):
        """Validar campos"""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class BaseMemory(ABC):
    """
    Interfaz abstracta para backends de memoria long-term

    Implementaciones:
    - SQLiteMemory: keyword search en SQLite
    - ChromaMemory: semantic search con embeddings
    - HybridMemory: combinación de ambos
    """

    @abstractmethod
    def save_turn(
        self,
        session_id: str,
        user_msg: str,
        agent_msg: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Guardar un turno de conversación en memoria long-term

        Args:
            session_id: ID único de la sesión
            user_msg: Mensaje del usuario
            agent_msg: Respuesta del agente
            metadata: Datos adicionales (topic, etc)
        """
        pass

    @abstractmethod
    def search_relevant(
        self,
        query: str,
        top_k: int = 3,
        exclude_session: Optional[str] = None
    ) -> List[MemoryEntry]:
        """
        Buscar memories relevantes para una query

        Args:
            query: Pregunta o texto para buscar
            top_k: Número de resultados a retornar
            exclude_session: Session ID a excluir (para no traer la sesión actual)

        Returns:
            Lista de MemoryEntry ordenadas por relevancia (mejor primero)
        """
        pass

    @abstractmethod
    def get_session_history(self, session_id: str) -> List[MemoryEntry]:
        """
        Obtener todo el historial de una sesión

        Args:
            session_id: ID de la sesión

        Returns:
            Lista de todos los turnos de esa sesión en orden cronológico
        """
        pass

    @abstractmethod
    def clear_session(self, session_id: str) -> None:
        """
        Limpiar todos los memories de una sesión específica

        Args:
            session_id: ID de la sesión a limpiar
        """
        pass

    @abstractmethod
    def clear_all(self) -> None:
        """Limpiar toda la memoria long-term (DESTRUCTIVO)"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de la memoria

        Returns:
            Dict con: total_turns, total_sessions, backend_type, db_size, etc
        """
        pass
