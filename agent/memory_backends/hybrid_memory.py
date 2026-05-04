"""
Hybrid Long-Term Memory backend

Combines SQLite (for durability & keyword search) + ChromaDB (for semantic search)
Saves to both, searches with ChromaDB, fallback to SQLite on error
"""

from typing import List, Dict, Any, Optional
from .base import BaseMemory, MemoryEntry
from .sqlite_memory import SQLiteMemory

try:
    from .chroma_memory import ChromaMemory
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


class HybridMemory(BaseMemory):
    """
    Backend híbrido que usa SQLite + ChromaDB

    Ventajas:
    - Durabilidad: SQLite es confiable y simple
    - Búsqueda semántica: ChromaDB es potente
    - Resilencia: Si ChromaDB falla, fallback a SQLite

    Desventajas:
    - Requiere más espacio (dos bases de datos)
    - Más lento en save (duplica escrituras)
    """

    def __init__(self, sqlite_db: str = "long_term_memory.db", chroma_dir: str = "chroma_db"):
        """
        Inicializar backend híbrido

        Args:
            sqlite_db: Ruta a SQLite DB
            chroma_dir: Directorio para ChromaDB
        """
        self.sqlite = SQLiteMemory(db_path=sqlite_db)

        try:
            self.chroma = ChromaMemory(persist_dir=chroma_dir) if CHROMA_AVAILABLE else None
        except Exception as e:
            print(f"[Warning] ChromaDB initialization failed: {e}. Using SQLite fallback.")
            self.chroma = None

    def save_turn(
        self,
        session_id: str,
        user_msg: str,
        agent_msg: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Guardar en ambos backends"""
        # Siempre guardar en SQLite (más confiable)
        self.sqlite.save_turn(session_id, user_msg, agent_msg, metadata)

        # Intentar guardar en ChromaDB
        if self.chroma:
            try:
                self.chroma.save_turn(session_id, user_msg, agent_msg, metadata)
            except Exception as e:
                print(f"[Warning] ChromaDB save failed: {e}. Saved to SQLite only.")

    def search_relevant(
        self,
        query: str,
        top_k: int = 3,
        exclude_session: Optional[str] = None
    ) -> List[MemoryEntry]:
        """
        Buscar primero con ChromaDB (semántico), fallback a SQLite (keywords)
        """
        # Intentar ChromaDB primero (mejor búsqueda semántica)
        if self.chroma:
            try:
                results = self.chroma.search_relevant(query, top_k, exclude_session)
                if results:
                    return results
            except Exception as e:
                print(f"[Warning] ChromaDB search failed: {e}. Falling back to SQLite.")

        # Fallback a SQLite keyword search
        return self.sqlite.search_relevant(query, top_k, exclude_session)

    def get_session_history(self, session_id: str) -> List[MemoryEntry]:
        """
        Obtener historial de una sesión (SQLite es más confiable)
        """
        return self.sqlite.get_session_history(session_id)

    def clear_session(self, session_id: str) -> None:
        """Limpiar una sesión de ambos backends"""
        self.sqlite.clear_session(session_id)
        if self.chroma:
            try:
                self.chroma.clear_session(session_id)
            except Exception as e:
                print(f"[Warning] ChromaDB clear_session failed: {e}")

    def clear_all(self) -> None:
        """Limpiar ambos backends (DESTRUCTIVO)"""
        self.sqlite.clear_all()
        if self.chroma:
            try:
                self.chroma.clear_all()
            except Exception as e:
                print(f"[Warning] ChromaDB clear_all failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de ambos backends"""
        sqlite_stats = self.sqlite.get_stats()
        chroma_stats = {}

        if self.chroma:
            try:
                chroma_stats = self.chroma.get_stats()
            except Exception as e:
                chroma_stats = {"error": str(e)}

        return {
            "backend_type": "hybrid",
            "sqlite": sqlite_stats,
            "chroma": chroma_stats if chroma_stats else "Not initialized",
        }
