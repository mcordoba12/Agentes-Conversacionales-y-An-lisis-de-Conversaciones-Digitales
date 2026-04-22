"""
Influence Metrics MCP - FastAPI Service
Analiza la influencia de actores y posts en la conversacion

Endpoint:
  GET /analisis/metricas

Respuesta:
  {
    "top_autores": [...],
    "top_posts": [...],
    "autores_mas_activos": [...],
    "estadisticas_generales": {...}
  }
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

import uvicorn
import pandas as pd
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel

# Agregar proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared import get_loader
import config

# ==============================================================================
# MODELOS
# ==============================================================================

class AuthorMetric(BaseModel):
    """Metrica de un autor"""
    autor: str
    influence_score: float
    cantidad_posts: int
    cantidad_respuestas: int
    engagement_rate: float


class PostMetric(BaseModel):
    """Metrica de un post"""
    post_id: str
    autor: str
    cantidad_respuestas: int
    influence_score: float
    texto_preview: str
    timestamp: Optional[str]


class InfluenceResponse(BaseModel):
    """Respuesta del analisis de influencia"""
    top_autores_por_influencia: List[AuthorMetric]
    top_posts_comentados: List[PostMetric]
    autores_mas_activos: List[AuthorMetric]
    estadisticas_generales: Dict[str, Any]


# ==============================================================================
# LOGICA DE ANALISIS
# ==============================================================================

class InfluenceAnalyzer:
    """
    Analiza la influencia de actores en las conversaciones
    Usa procesamiento determinístico con Pandas
    """

    def __init__(self, dataframe):
        self.df = dataframe
        self._build_metrics_cache()

    def _build_metrics_cache(self):
        """Precalcular metricas para performance"""
        # Contar respuestas por post (parentId)
        self.reply_counts = self.df['parentId'].value_counts()

        # Metricas por autor
        self.author_posts = self.df.groupby('author').size().rename('cantidad_posts')
        self.author_is_reply = self.df.groupby('author')['parentId'].apply(
            lambda x: (x.notna() & (x != '')).sum()
        ).rename('cantidad_respuestas')
        self.author_influence = self.df.groupby('author')['influenceScore'].apply(
            lambda x: pd.to_numeric(x, errors='coerce').sum()
        ).rename('influence_score_total')

    def get_top_autores_por_influencia(self, limit: int = 10) -> List[AuthorMetric]:
        """Top autores por influenceScore total"""
        metrics = pd.DataFrame({
            'influence_score': self.author_influence,
            'cantidad_posts': self.author_posts,
            'cantidad_respuestas': self.author_is_reply,
        }).fillna(0)

        # Calcular engagement rate
        metrics['engagement_rate'] = (
            metrics['cantidad_respuestas'] / metrics['cantidad_posts']
        ).fillna(0)

        # Filtrar autores con nombre vacio y ordenar
        metrics = metrics[metrics.index != '']
        metrics = metrics.sort_values('influence_score', ascending=False)

        result = []
        for idx, (author, row) in enumerate(metrics.head(limit).iterrows()):
            result.append(AuthorMetric(
                autor=author,
                influence_score=round(float(row['influence_score']), 2),
                cantidad_posts=int(row['cantidad_posts']),
                cantidad_respuestas=int(row['cantidad_respuestas']),
                engagement_rate=round(float(row['engagement_rate']), 3)
            ))

        return result

    def get_top_posts_comentados(self, limit: int = 10) -> List[PostMetric]:
        """Top posts por cantidad de respuestas"""
        # Crear columna de cantidad de respuestas
        self.df['reply_count'] = self.df['id'].map(self.reply_counts).fillna(0).astype(int)

        # Filtrar posts principales (sin parentId o parentId vacio)
        main_posts = self.df[self.df['parentId'].isna() | (self.df['parentId'] == '')]

        # Ordenar por cantidad de respuestas
        top_posts = main_posts.nlargest(limit, 'reply_count')

        result = []
        for idx, row in top_posts.iterrows():
            post_id = str(row['id']).strip()
            author = str(row['author']).strip()
            reply_count = int(row['reply_count'])
            influence = row.get('influenceScore', 0)

            # Parsear timestamp
            ts = self._parse_timestamp(row.get('createdAt'))
            ts_str = ts.isoformat() if ts else None

            # Preview del texto
            text = str(row.get('text', ''))[:100].strip()

            result.append(PostMetric(
                post_id=post_id,
                autor=author,
                cantidad_respuestas=reply_count,
                influence_score=float(influence) if influence == influence else 0,  # NaN check
                texto_preview=text,
                timestamp=ts_str
            ))

        return result

    def get_autores_mas_activos(self, limit: int = 10) -> List[AuthorMetric]:
        """Top autores por cantidad de posts"""
        metrics = pd.DataFrame({
            'influence_score': self.author_influence,
            'cantidad_posts': self.author_posts,
            'cantidad_respuestas': self.author_is_reply,
        }).fillna(0)

        metrics['engagement_rate'] = (
            metrics['cantidad_respuestas'] / metrics['cantidad_posts']
        ).fillna(0)

        metrics = metrics[metrics.index != '']
        metrics = metrics.sort_values('cantidad_posts', ascending=False)

        result = []
        for author, row in metrics.head(limit).iterrows():
            result.append(AuthorMetric(
                autor=author,
                influence_score=round(float(row['influence_score']), 2),
                cantidad_posts=int(row['cantidad_posts']),
                cantidad_respuestas=int(row['cantidad_respuestas']),
                engagement_rate=round(float(row['engagement_rate']), 3)
            ))

        return result

    def get_estadisticas_generales(self) -> Dict[str, Any]:
        """Estadisticas generales de la conversacion"""
        total_posts = len(self.df)
        total_authors = self.df['author'].nunique()

        # Posts principales vs respuestas
        main_posts = len(self.df[self.df['parentId'].isna() | (self.df['parentId'] == '')])
        replies = total_posts - main_posts

        # Influencia promedio
        influence_values = pd.to_numeric(self.df['influenceScore'], errors='coerce')
        avg_influence = influence_values.mean()

        # Autores unicos
        non_empty_authors = len(self.author_posts[self.author_posts.index != ''])

        return {
            "total_posts": int(total_posts),
            "total_autores": int(total_authors),
            "autores_con_nombre": int(non_empty_authors),
            "posts_principales": int(main_posts),
            "respuestas_totales": int(replies),
            "ratio_respuestas": round(replies / total_posts if total_posts > 0 else 0, 3),
            "influencia_promedio": round(float(avg_influence), 2),
            "influencia_maxima": round(float(influence_values.max()), 2),
            "influencia_minima": round(float(influence_values.min()), 2),
        }

    def _parse_timestamp(self, ts) -> Optional[datetime]:
        """Parsear timestamp de diferentes formatos"""
        if ts is None or ts != ts:  # NaN check
            return None

        ts = str(ts).strip()
        if not ts:
            return None

        try:
            # Milisegundos desde epoch
            if ts.isdigit() and len(ts) == 13:
                return datetime.fromtimestamp(int(ts) / 1000)
            # ISO format
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except:
            return None

    def analyze(self) -> InfluenceResponse:
        """Realizar analisis completo de influencia"""
        return InfluenceResponse(
            top_autores_por_influencia=self.get_top_autores_por_influencia(),
            top_posts_comentados=self.get_top_posts_comentados(),
            autores_mas_activos=self.get_autores_mas_activos(),
            estadisticas_generales=self.get_estadisticas_generales()
        )


# ==============================================================================
# FASTAPI APP
# ==============================================================================

app = FastAPI(
    title="Influence Metrics MCP",
    description="Analiza la influencia de actores y posts en conversaciones digitales",
    version="1.0.0"
)

# Inicializar analyzer
loader = get_loader()
analyzer = InfluenceAnalyzer(loader.df)
cache = {}


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "Influence Metrics MCP",
        "port": config.INFLUENCE_MCP_PORT
    }


@app.get("/analisis/metricas", response_model=InfluenceResponse)
async def get_influence_metrics():
    """
    Obtener metricas de influencia del dataset completo

    Returns:
        InfluenceResponse con:
        - Top 10 autores por influenceScore
        - Top 10 posts mas comentados
        - Top 10 autores mas activos
        - Estadisticas generales
    """
    cache_key = "metricas_globales"

    # Verificar cache
    if cache_key in cache:
        return cache[cache_key]

    try:
        result = analyzer.analyze()
        cache[cache_key] = result
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en analisis: {str(e)}")


@app.get("/analisis/metricas/autores")
async def get_top_autores(limit: int = Query(10, ge=1, le=100)):
    """Top autores por influencia"""
    try:
        return {
            "top_autores": analyzer.get_top_autores_por_influencia(limit)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analisis/metricas/posts")
async def get_top_posts(limit: int = Query(10, ge=1, le=100)):
    """Top posts mas comentados"""
    try:
        return {
            "top_posts": analyzer.get_top_posts_comentados(limit)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    print(f"\n[STARTING] Influence Metrics MCP on port {config.INFLUENCE_MCP_PORT}")
    print(f"[INFO] Dataset: {loader.get_stats()['rows']} rows loaded")
    print(f"[INFO] Metrics precalculated")
    print(f"\n[READY] Influence Metrics MCP listening on http://localhost:{config.INFLUENCE_MCP_PORT}")
    print(f"[READY] API docs at http://localhost:{config.INFLUENCE_MCP_PORT}/docs\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.INFLUENCE_MCP_PORT,
        log_level="info"
    )
