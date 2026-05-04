"""
Metrics Store — JSON persistence for dashboard metrics
Permite que el agente CLI escriba métricas que el dashboard Streamlit lee
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any

# NO importar config.py — evita error de OPENAI_API_KEY
METRICS_FILE = Path(__file__).parent.parent / "data" / "dashboard_metrics.json"


def append_metric(record: Dict[str, Any]) -> None:
    """
    Agregar un registro de métrica al archivo JSON

    Args:
        record: Dict con campos: query_id, timestamp, latency_ms, tool_called, etc.

    Se usa tras cada query del agente para persistir datos para el dashboard
    """
    try:
        # Asegurar que el directorio data/ existe
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Leer JSON existente
        records = []
        if METRICS_FILE.exists():
            try:
                with open(METRICS_FILE, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        records = json.loads(content)
            except (json.JSONDecodeError, IOError):
                # Si el archivo está corrupto, comenzar de nuevo
                records = []

        # Agregar nuevo registro
        records.append(record)

        # Escribir atómicamente (write to .tmp, then rename)
        tmp_file = str(METRICS_FILE) + ".tmp"
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

        # Rename atómico (funciona en Windows y Linux)
        os.replace(tmp_file, str(METRICS_FILE))

    except Exception as e:
        # Nunca crashear el agente por culpa de métricas
        pass


def read_metrics() -> List[Dict[str, Any]]:
    """
    Leer todos los registros de métricas del archivo JSON

    Returns:
        Lista de dicts con métricas. [] si el archivo no existe o está corrupto.

    Usado por el dashboard Streamlit para cargar datos
    """
    try:
        if not METRICS_FILE.exists():
            return []

        with open(METRICS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)

    except (json.JSONDecodeError, IOError):
        # Si el archivo está corrupto, retornar lista vacía (no crashear)
        return []


def clear_metrics() -> None:
    """
    Limpiar todos los registros de métricas (útil para reset del dashboard)
    """
    try:
        if METRICS_FILE.exists():
            with open(METRICS_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
    except Exception:
        pass
