"""
Memory Backends for Long-Term Memory (Phase 3)

Provides 3 pluggable backends:
- SQLiteMemory: keyword search in SQLite
- ChromaMemory: semantic search with embeddings
- HybridMemory: combination of both
"""

from .base import BaseMemory, MemoryEntry
from .factory import create_memory_backend

__all__ = ["BaseMemory", "MemoryEntry", "create_memory_backend"]
