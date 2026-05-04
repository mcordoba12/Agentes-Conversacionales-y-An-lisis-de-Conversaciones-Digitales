"""
ChromaDB-based Long-Term Memory backend

Stores conversations with semantic embeddings using ChromaDB
Enables semantic search for relevant past interactions
"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from .base import BaseMemory, MemoryEntry


class ChromaMemory(BaseMemory):
    """
    Backend de memoria en ChromaDB con búsqueda semántica

    Usa sentence-transformers para embeddings y ChromaDB para persistencia
    """

    def __init__(self, persist_dir: str = "chroma_db"):
        """
        Inicializar backend ChromaDB

        Args:
            persist_dir: Directorio donde guardar la base de datos ChromaDB

        Raises:
            ImportError: Si chromadb no está instalado
        """
        if not CHROMA_AVAILABLE:
            raise ImportError(
                "chromadb no está instalado. "
                "Instala: pip install chromadb sentence-transformers"
            )

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Inicializar ChromaDB client
        settings = Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(self.persist_dir),
            anonymized_telemetry=False,
            allow_reset=True
        )
        self.client = chromadb.Client(settings)

        # Obtener o crear collection
        self.collection = self.client.get_or_create_collection(
            name="lt_memory",
            metadata={
                "description": "Long-term memory collection for conversation history",
                "model": "all-MiniLM-L6-v2"  # Default sentence-transformers model
            }
        )

        # Contador interno para generar IDs únicos
        self._turn_id_counter = self._get_next_id()

    def _get_next_id(self) -> int:
        """Obtener el próximo ID disponible"""
        count = self.collection.count()
        return count + 1

    def save_turn(
        self,
        session_id: str,
        user_msg: str,
        agent_msg: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Guardar un turno con embeddings en ChromaDB"""
        metadata = metadata or {}
        timestamp = datetime.now().isoformat()

        # Document = combinación de user_msg + agent_msg para mejor embedding
        document = f"User: {user_msg}\n\nAssistant: {agent_msg}"

        # Metadatos para recuperar después
        doc_metadata = {
            "session_id": session_id,
            "timestamp": timestamp,
            "topic": metadata.get("topic", "general"),
        }

        # ChromaDB genera embeddings automáticamente
        self.collection.add(
            ids=[str(self._turn_id_counter)],
            documents=[document],
            metadatas=[doc_metadata]
        )

        self._turn_id_counter += 1

    def search_relevant(
        self,
        query: str,
        top_k: int = 3,
        exclude_session: Optional[str] = None
    ) -> List[MemoryEntry]:
        """
        Buscar memories relevantes por similitud semántica

        ChromaDB genera embeddings automáticamente y busca por cosine similarity
        """
        try:
            # Buscar en ChromaDB
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k * 2  # Buscar más para filtrar por sesión si es necesario
            )

            entries = []

            if results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i] if results["distances"] else 0

                    # Filtrar sesión si se especifica
                    if exclude_session and metadata["session_id"] == exclude_session:
                        continue

                    # Recuperar el documento original para extraer user_msg y agent_msg
                    # Nota: ChromaDB no retorna documentos en query, necesitamos get()
                    # Para simplificar, reconstruimos desde metadata
                    # En producción, querrías guardar user_msg y agent_msg por separado en metadata

                    entries.append(MemoryEntry(
                        session_id=metadata["session_id"],
                        user_msg="[past interaction]",  # ChromaDB no retorna el doc en query
                        agent_msg="[past interaction]",
                        timestamp=metadata["timestamp"],
                        topic=metadata.get("topic", "general"),
                        relevance_score=1.0 - distance  # Convertir distance a relevance
                    ))

                    if len(entries) >= top_k:
                        break

            return entries

        except Exception as e:
            # Si hay error en ChromaDB, retornar lista vacía
            # En producción, sería mejor hacer fallback a SQLite
            print(f"[Warning] ChromaDB search error: {e}")
            return []

    def get_session_history(self, session_id: str) -> List[MemoryEntry]:
        """
        Obtener historial completo de una sesión

        ChromaDB no tiene WHERE clause, así que hacemos query general y filtramos
        """
        try:
            # Obtener todos los documentos (hay límite por defecto)
            results = self.collection.get(
                where={"session_id": session_id}
            )

            entries = []
            if results["ids"]:
                for i, doc_id in enumerate(results["ids"]):
                    metadata = results["metadatas"][i]
                    entries.append(MemoryEntry(
                        session_id=metadata["session_id"],
                        user_msg="[history entry]",
                        agent_msg="[history entry]",
                        timestamp=metadata["timestamp"],
                        topic=metadata.get("topic", "general")
                    ))

            # Ordenar por timestamp
            entries.sort(key=lambda x: x.timestamp)
            return entries

        except Exception as e:
            print(f"[Warning] ChromaDB get_session_history error: {e}")
            return []

    def clear_session(self, session_id: str) -> None:
        """Limpiar una sesión de ChromaDB"""
        try:
            # ChromaDB delete con where clause
            self.collection.delete(
                where={"session_id": session_id}
            )
        except Exception as e:
            print(f"[Warning] ChromaDB clear_session error: {e}")

    def clear_all(self) -> None:
        """Limpiar toda la colección"""
        try:
            self.client.delete_collection(name="lt_memory")
            self.collection = self.client.get_or_create_collection(
                name="lt_memory",
                metadata={
                    "description": "Long-term memory collection for conversation history"
                }
            )
        except Exception as e:
            print(f"[Warning] ChromaDB clear_all error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de ChromaDB"""
        try:
            count = self.collection.count()

            # Obtener todos para estadísticas (puede ser lento si hay muchos)
            all_docs = self.collection.get()
            sessions = set()
            oldest = None
            newest = None

            if all_docs["metadatas"]:
                for metadata in all_docs["metadatas"]:
                    sessions.add(metadata["session_id"])
                    timestamp = metadata["timestamp"]
                    if not oldest or timestamp < oldest:
                        oldest = timestamp
                    if not newest or timestamp > newest:
                        newest = timestamp

            # Tamaño del directorio
            dir_size_mb = 0
            if self.persist_dir.exists():
                for file in self.persist_dir.rglob("*"):
                    if file.is_file():
                        dir_size_mb += file.stat().st_size / (1024 * 1024)

            return {
                "backend_type": "chroma",
                "total_turns": count,
                "total_sessions": len(sessions),
                "oldest_entry": oldest,
                "newest_entry": newest,
                "persist_dir_mb": round(dir_size_mb, 2),
                "persist_dir": str(self.persist_dir),
            }

        except Exception as e:
            print(f"[Warning] ChromaDB get_stats error: {e}")
            return {
                "backend_type": "chroma",
                "error": str(e)
            }
