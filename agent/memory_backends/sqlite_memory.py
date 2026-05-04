"""
SQLite-based Long-Term Memory backend

Stores conversations in SQLite with keyword search
Simplest backend, no external dependencies
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base import BaseMemory, MemoryEntry


class SQLiteMemory(BaseMemory):
    """
    Backend de memoria en SQLite con búsqueda por keywords

    Tabla: memory_turns
    - id (INTEGER PRIMARY KEY)
    - session_id (TEXT)
    - user_msg (TEXT)
    - agent_msg (TEXT)
    - timestamp (TEXT ISO format)
    - topic (TEXT, nullable)
    """

    def __init__(self, db_path: str = "long_term_memory.db"):
        """
        Inicializar backend SQLite

        Args:
            db_path: Ruta al archivo SQLite
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Crear tabla si no existe
        self._init_db()

    def _init_db(self):
        """Crear tabla memory_turns si no existe"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_msg TEXT NOT NULL,
                    agent_msg TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    topic TEXT
                )
            """)

            # Crear índices para búsqueda rápida
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session ON memory_turns(session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON memory_turns(timestamp)
            """)

            conn.commit()

    def save_turn(
        self,
        session_id: str,
        user_msg: str,
        agent_msg: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Guardar un turno en SQLite"""
        metadata = metadata or {}
        timestamp = datetime.now().isoformat()
        topic = metadata.get("topic")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memory_turns (session_id, user_msg, agent_msg, timestamp, topic)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, user_msg, agent_msg, timestamp, topic))
            conn.commit()

    def search_relevant(
        self,
        query: str,
        top_k: int = 3,
        exclude_session: Optional[str] = None
    ) -> List[MemoryEntry]:
        """
        Buscar memories relevantes por keyword

        Estrategia: LIKE en user_msg Y agent_msg, ordenado por timestamp DESC
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Query LIKE con wildcards
            search_pattern = f"%{query}%"
            exclude_clause = "AND session_id != ?" if exclude_session else ""

            sql = f"""
                SELECT session_id, user_msg, agent_msg, timestamp, topic
                FROM memory_turns
                WHERE (user_msg LIKE ? OR agent_msg LIKE ?)
                {exclude_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            """

            params = [search_pattern, search_pattern]
            if exclude_session:
                params.append(exclude_session)
            params.append(top_k)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # Convertir a MemoryEntry
            entries = []
            for row in rows:
                session_id, user_msg, agent_msg, timestamp, topic = row
                entries.append(MemoryEntry(
                    session_id=session_id,
                    user_msg=user_msg,
                    agent_msg=agent_msg,
                    timestamp=timestamp,
                    topic=topic,
                    relevance_score=0.0  # SQLite no retorna relevance, score por defecto
                ))

            return entries

    def get_session_history(self, session_id: str) -> List[MemoryEntry]:
        """Obtener todo el historial de una sesión"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT session_id, user_msg, agent_msg, timestamp, topic
                FROM memory_turns
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,))

            rows = cursor.fetchall()
            entries = []
            for row in rows:
                session_id, user_msg, agent_msg, timestamp, topic = row
                entries.append(MemoryEntry(
                    session_id=session_id,
                    user_msg=user_msg,
                    agent_msg=agent_msg,
                    timestamp=timestamp,
                    topic=topic
                ))

            return entries

    def clear_session(self, session_id: str) -> None:
        """Limpiar una sesión"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memory_turns WHERE session_id = ?", (session_id,))
            conn.commit()

    def clear_all(self) -> None:
        """Limpiar toda la memoria"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memory_turns")
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total de turns
            cursor.execute("SELECT COUNT(*) FROM memory_turns")
            total_turns = cursor.fetchone()[0]

            # Total de sesiones
            cursor.execute("SELECT COUNT(DISTINCT session_id) FROM memory_turns")
            total_sessions = cursor.fetchone()[0]

            # Timestamps
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM memory_turns")
            oldest, newest = cursor.fetchone()

            # Tamaño del archivo
            db_size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0

            return {
                "backend_type": "sqlite",
                "total_turns": total_turns,
                "total_sessions": total_sessions,
                "oldest_entry": oldest,
                "newest_entry": newest,
                "db_size_mb": round(db_size_mb, 2),
                "db_path": str(self.db_path),
            }
