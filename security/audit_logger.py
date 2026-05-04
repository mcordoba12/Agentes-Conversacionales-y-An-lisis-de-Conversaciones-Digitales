"""
Audit Logger
Registra todas las interacciones del usuario para auditoría y compliance
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import hashlib


class AuditLogger:
    """Logger de auditoría que guarda en SQLite"""

    def __init__(self, db_path: str = "data/audit.db"):
        """
        Inicializar audit logger

        Args:
            db_path: Ruta de la base de datos SQLite
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Crear tabla si no existe"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT NOT NULL,
                user_id TEXT,
                query TEXT NOT NULL,
                query_hash TEXT,
                has_injection BOOLEAN DEFAULT 0,
                injection_severity TEXT,
                pii_detected BOOLEAN DEFAULT 0,
                pii_types TEXT,
                tool_called TEXT,
                response_length INTEGER,
                response_hash TEXT,
                error TEXT,
                metadata TEXT
            )
        """)

        # Crear índices para búsquedas rápidas
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON audit_log(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_injection ON audit_log(has_injection)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pii ON audit_log(pii_detected)")

        conn.commit()
        conn.close()

    def log(
        self,
        session_id: str,
        query: str,
        tool_called: Optional[str] = None,
        response: Optional[str] = None,
        has_injection: bool = False,
        injection_severity: str = "SAFE",
        pii_detected: bool = False,
        pii_types: Optional[str] = None,
        user_id: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Registrar una interacción

        Args:
            session_id: ID de la sesión
            query: Pregunta del usuario
            tool_called: Herramienta que se llamó (si aplica)
            response: Respuesta del agente
            has_injection: Si se detectó inyección
            injection_severity: Severidad ("SAFE", "LOW", "MEDIUM", "HIGH")
            pii_detected: Si se detectó PII
            pii_types: Tipos de PII encontrados (JSON string)
            user_id: ID del usuario (opcional)
            error: Error si ocurrió
            metadata: Metadatos adicionales

        Returns:
            ID del registro creado
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Generar hashes
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        response_hash = hashlib.sha256((response or "").encode()).hexdigest()[:16] if response else None

        metadata_json = json.dumps(metadata or {})

        try:
            cursor.execute("""
                INSERT INTO audit_log (
                    session_id, user_id, query, query_hash,
                    has_injection, injection_severity,
                    pii_detected, pii_types,
                    tool_called, response_length, response_hash,
                    error, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, user_id, query, query_hash,
                has_injection, injection_severity,
                pii_detected, pii_types,
                tool_called, len(response or ""), response_hash,
                error, metadata_json
            ))

            conn.commit()
            record_id = cursor.lastrowid

            return record_id

        except Exception as e:
            print(f"Error logging audit: {e}")
            return -1

        finally:
            conn.close()

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Obtener resumen de una sesión"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_queries,
                SUM(CASE WHEN has_injection THEN 1 ELSE 0 END) as injection_attempts,
                SUM(CASE WHEN pii_detected THEN 1 ELSE 0 END) as pii_detections,
                GROUP_CONCAT(DISTINCT tool_called) as tools_used,
                MAX(timestamp) as last_activity
            FROM audit_log
            WHERE session_id = ?
        """, (session_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        else:
            return {
                "total_queries": 0,
                "injection_attempts": 0,
                "pii_detections": 0,
                "tools_used": None,
                "last_activity": None,
            }

    def get_security_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Generar reporte de seguridad de las últimas N horas

        Args:
            hours: Últimas N horas a incluir

        Returns:
            Reporte agregado
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT
                COUNT(*) as total_queries,
                COUNT(DISTINCT session_id) as unique_sessions,
                SUM(CASE WHEN has_injection THEN 1 ELSE 0 END) as injection_attempts,
                SUM(CASE WHEN pii_detected THEN 1 ELSE 0 END) as pii_detections,
                injection_severity,
                COUNT(*) as severity_count
            FROM audit_log
            WHERE timestamp > datetime('now', '-{hours} hours')
            GROUP BY injection_severity
        """)

        rows = cursor.fetchall()
        conn.close()

        severity_breakdown = {row["injection_severity"]: row["severity_count"] for row in rows}

        return {
            "period": f"Last {hours} hours",
            "total_queries": sum(row["total_queries"] for row in rows) or 0,
            "unique_sessions": rows[0]["unique_sessions"] if rows else 0,
            "injection_attempts": rows[0]["injection_attempts"] if rows else 0,
            "pii_detections": rows[0]["pii_detections"] if rows else 0,
            "severity_breakdown": severity_breakdown,
        }

    def export_logs(self, session_id: Optional[str] = None, output_file: Optional[str] = None) -> str:
        """
        Exportar logs a JSON

        Args:
            session_id: Si es None, exporta todos los logs
            output_file: Archivo de salida (si es None, usa stdout)

        Returns:
            JSON string
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if session_id:
            cursor.execute("SELECT * FROM audit_log WHERE session_id = ? ORDER BY timestamp DESC", (session_id,))
        else:
            cursor.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 1000")

        rows = cursor.fetchall()
        conn.close()

        data = [dict(row) for row in rows]
        json_str = json.dumps(data, indent=2, default=str)

        if output_file:
            Path(output_file).write_text(json_str)

        return json_str
