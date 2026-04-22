"""
Propagation MCP - FastAPI Service
Analiza la propagacion de un mensaje en la red

Endpoint:
  GET /analisis/propagacion?post_id=XXX

Respuesta:
  {
    "id_original": "...",
    "alcance": 43,
    "velocidad_media": "5 minutos",
    "profundidad": 3,
    "hijos_directos": 12,
    "tiempo_inicio": "2024-12-05 10:00:00",
    "tiempo_ultimo": "2024-12-05 11:45:00",
    "arbol_estructura": {...}
  }
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from collections import deque

import uvicorn
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel

# Agregar proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import get_loader
import config

# ==============================================================================
# MODELOS
# ==============================================================================

class PropagationResponse(BaseModel):
    """Respuesta del análisis de propagación"""
    id_original: str
    alcance_total: int  # Total de respuestas
    hijos_directos: int  # Respuestas al post original
    profundidad_maxima: int  # Nivel máximo en el árbol
    velocidad_media_minutos: float  # Tiempo promedio entre respuestas
    velocidad_max_minutos: float  # Respuesta más rápida
    velocidad_min_minutos: float  # Respuesta más lenta
    timestamp_original: Optional[str]  # Timestamp del post original
    timestamp_primer_respuesta: Optional[str]
    timestamp_ultima_respuesta: Optional[str]
    duracion_total_horas: float  # Cuántas horas duró la propagación
    distribucion_por_nivel: Dict[int, int]  # {nivel: cantidad_de_posts}
    top_autores_respuestas: Dict[str, int]  # Top autores que respondieron


# ==============================================================================
# LÓGICA DE PROPAGACIÓN (BFS)
# ==============================================================================

class PropagationAnalyzer:
    """
    Analiza la propagación de un mensaje usando BFS (Breadth-First Search)
    """

    def __init__(self, dataframe):
        self.df = dataframe
        # Crear índice de parentId para búsqueda rápida
        self.children_index = self._build_children_index()

    def _build_children_index(self) -> Dict[str, List[int]]:
        """
        Crear índice para búsqueda rápida de hijos
        Mapeo: parentId -> [list of row indices]
        """
        children_index = {}

        for idx, row in self.df.iterrows():
            parent_id = row.get('parentId')

            # Skip si no tiene parentId válido
            if parent_id is None or parent_id == '' or parent_id != parent_id:  # NaN check
                continue

            parent_id = str(parent_id).strip()
            if parent_id not in children_index:
                children_index[parent_id] = []

            children_index[parent_id].append(idx)

        return children_index

    def analyze(self, post_id: str) -> PropagationResponse:
        """
        Analizar propagación de un post específico usando BFS
        """
        post_id = str(post_id).strip()

        # Verificar que el post existe
        post_rows = self.df[self.df['id'] == post_id]
        if len(post_rows) == 0:
            raise ValueError(f"Post con ID '{post_id}' no encontrado")

        # Obtener datos del post original
        original_post = post_rows.iloc[0]
        original_timestamp = self._parse_timestamp(original_post.get('createdAt'))

        # BFS para encontrar todos los hijos
        queue = deque([(post_id, 0)])  # (post_id, nivel)
        visited = set([post_id])

        hijos_totales = []  # [(nivel, idx, timestamp, author)]
        hijos_directos = 0
        distribucion_por_nivel = {}

        while queue:
            current_id, nivel = queue.popleft()

            # Obtener hijos de este post
            if current_id in self.children_index:
                for child_idx in self.children_index[current_id]:
                    if child_idx in visited:
                        continue

                    visited.add(child_idx)
                    child_row = self.df.iloc[child_idx]
                    child_id = str(child_row['id']).strip()
                    child_timestamp = self._parse_timestamp(child_row.get('createdAt'))
                    child_author = str(child_row.get('author', 'unknown')).strip()

                    # Registrar en nivel correcto
                    hijo_nivel = nivel + 1
                    hijos_totales.append((hijo_nivel, child_idx, child_timestamp, child_author))

                    if hijo_nivel == 1:
                        hijos_directos += 1

                    # Distribución por nivel
                    if hijo_nivel not in distribucion_por_nivel:
                        distribucion_por_nivel[hijo_nivel] = 0
                    distribucion_por_nivel[hijo_nivel] += 1

                    # Agregar a queue para BFS
                    queue.append((child_id, hijo_nivel))

        # Calcular métricas
        alcance_total = len(hijos_totales)
        profundidad = max(distribucion_por_nivel.keys()) if distribucion_por_nivel else 0

        # Métricas de tiempo
        velocidades = []
        primer_timestamp = None
        ultimo_timestamp = None
        top_autores = {}

        if hijos_totales:
            # Ordenar por timestamp para calcular velocidades
            hijos_ordenados = sorted(hijos_totales, key=lambda x: x[2] if x[2] else datetime.min)

            for nivel, idx, ts, author in hijos_ordenados:
                if ts and original_timestamp:
                    delta_minutos = (ts - original_timestamp).total_seconds() / 60
                    velocidades.append(delta_minutos)

                if primer_timestamp is None:
                    primer_timestamp = ts
                if ts:
                    ultimo_timestamp = ts

                # Contar autores
                top_autores[author] = top_autores.get(author, 0) + 1

        # Calcular velocidad media
        velocidad_media = sum(velocidades) / len(velocidades) if velocidades else 0
        velocidad_max = max(velocidades) if velocidades else 0
        velocidad_min = min(velocidades) if velocidades else 0

        # Duración total
        duracion_horas = 0
        if primer_timestamp and ultimo_timestamp and original_timestamp:
            duracion = (ultimo_timestamp - original_timestamp).total_seconds() / 3600
            duracion_horas = max(0, duracion)

        # Top autores (top 5)
        top_autores_sorted = dict(sorted(top_autores.items(), key=lambda x: x[1], reverse=True)[:5])

        return PropagationResponse(
            id_original=post_id,
            alcance_total=alcance_total,
            hijos_directos=hijos_directos,
            profundidad_maxima=profundidad,
            velocidad_media_minutos=round(velocidad_media, 2),
            velocidad_max_minutos=round(velocidad_max, 2),
            velocidad_min_minutos=round(velocidad_min, 2),
            timestamp_original=original_timestamp.isoformat() if original_timestamp else None,
            timestamp_primer_respuesta=primer_timestamp.isoformat() if primer_timestamp else None,
            timestamp_ultima_respuesta=ultimo_timestamp.isoformat() if ultimo_timestamp else None,
            duracion_total_horas=round(duracion_horas, 2),
            distribucion_por_nivel=distribucion_por_nivel,
            top_autores_respuestas=top_autores_sorted
        )

    def _parse_timestamp(self, ts) -> Optional[datetime]:
        """Parsear timestamp de diferentes formatos"""
        if ts is None or ts != ts:  # NaN check
            return None

        ts = str(ts).strip()
        if not ts:
            return None

        try:
            # Intentar como milisegundos desde epoch
            if ts.isdigit() and len(ts) == 13:
                return datetime.fromtimestamp(int(ts) / 1000)
            # Intentar como ISO format
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except:
            return None


# ==============================================================================
# FASTAPI APP
# ==============================================================================

app = FastAPI(
    title="Propagation MCP",
    description="Analiza la propagacion de mensajes en conversaciones digitales",
    version="1.0.0"
)

# Inicializar analyzer con el dataframe
loader = get_loader()
analyzer = PropagationAnalyzer(loader.df)
cache = {}


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "Propagation MCP",
        "port": config.PROPAGATION_MCP_PORT
    }


@app.get("/analisis/propagacion", response_model=PropagationResponse)
async def analyze_propagation(post_id: str = Query(..., description="ID del post a analizar")):
    """
    Analizar la propagacion de un post específico

    Args:
        post_id: ID del post (ejemplo: c6adb4630994bdee807d387382d526bc)

    Returns:
        PropagationResponse con métricas detalladas de propagación
    """
    post_id = post_id.strip()

    # Verificar caché
    cache_key = f"propagacion::{post_id}"
    if cache_key in cache:
        return cache[cache_key]

    try:
        result = analyzer.analyze(post_id)
        # Guardar en caché
        cache[cache_key] = result
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis: {str(e)}")


@app.get("/health")
async def health():
    """Endpoint de health check"""
    stats = loader.get_stats()
    return {
        "status": "healthy",
        "dataset": stats,
        "cache_entries": len(cache)
    }


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    print(f"\n[STARTING] Propagation MCP on port {config.PROPAGATION_MCP_PORT}")
    print(f"[INFO] Dataset: {loader.get_stats()['rows']} rows loaded")
    print(f"[INFO] Children index built")
    print(f"\n[READY] Propagation MCP listening on http://localhost:{config.PROPAGATION_MCP_PORT}")
    print(f"[READY] API docs at http://localhost:{config.PROPAGATION_MCP_PORT}/docs\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.PROPAGATION_MCP_PORT,
        log_level="info"
    )
