"""
Factory para crear backends de memoria long-term
"""

from typing import Optional
from .base import BaseMemory
import config


def create_memory_backend(backend_type: Optional[str] = None) -> BaseMemory:
    """
    Factory function para crear un backend de memoria

    Args:
        backend_type: "sqlite" | "chroma" | "hybrid" | None (usa config default)

    Returns:
        Instancia de BaseMemory del tipo especificado

    Raises:
        ValueError: Si backend_type es inválido
        ImportError: Si faltan dependencias (ej: chromadb para chroma backend)
    """
    backend_type = backend_type or config.LT_MEMORY_BACKEND

    if backend_type == "sqlite":
        from .sqlite_memory import SQLiteMemory
        return SQLiteMemory(db_path=config.LT_MEMORY_DB)

    elif backend_type == "chroma":
        from .chroma_memory import ChromaMemory
        return ChromaMemory(persist_dir=config.CHROMA_PERSIST_DIR)

    elif backend_type == "hybrid":
        from .hybrid_memory import HybridMemory
        return HybridMemory(
            sqlite_db=config.LT_MEMORY_DB,
            chroma_dir=config.CHROMA_PERSIST_DIR
        )

    else:
        raise ValueError(
            f"Unknown memory backend: {backend_type}. "
            "Valid options: sqlite, chroma, hybrid"
        )
