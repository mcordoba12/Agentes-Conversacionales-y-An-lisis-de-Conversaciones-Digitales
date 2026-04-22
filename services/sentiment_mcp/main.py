"""
Sentiment MCP - FastAPI Service
Analiza los sentimientos de los posts y comentarios

Endpoint:
  GET /analisis/sentimiento

Respuesta:
  {
    "distribucion": {...},
    "sentimiento_dominante": "NEUTRAL",
    "muestras_por_sentimiento": {...}
  }
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List
from collections import Counter

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

class SentimentMetric(BaseModel):
    """Metrica de sentimiento"""
    sentimiento: str
    cantidad: int
    porcentaje: float


class SentimentResponse(BaseModel):
    """Respuesta del analisis de sentimientos"""
    distribucion: List[SentimentMetric]
    sentimiento_dominante: str
    porcentaje_dominante: float
    total_registros: int
    desconocidos: int
    cobertura: float
    muestras_por_sentimiento: Dict[str, List[str]]


# ==============================================================================
# LOGICA DE ANALISIS
# ==============================================================================

class SentimentAnalyzer:
    """
    Analiza los sentimientos en las conversaciones
    Usa etiquetas existentes en el dataset (87% de cobertura)
    """

    def __init__(self, dataframe):
        self.df = dataframe
        self._calculate_metrics()

    def _calculate_metrics(self):
        """Precalcular metricas de sentimiento"""
        self.sentiment_counts = self.df['sentiment'].value_counts()
        self.total_records = len(self.df)
        self.unknown_count = (self.df['sentiment'] == 'UNKNOWN').sum()
        self.known_count = self.total_records - self.unknown_count

    def get_distribution(self) -> List[SentimentMetric]:
        """Obtener distribucion de sentimientos"""
        result = []

        for sentiment, count in self.sentiment_counts.items():
            porcentaje = (count / self.total_records) * 100

            result.append(SentimentMetric(
                sentimiento=sentiment,
                cantidad=int(count),
                porcentaje=round(porcentaje, 2)
            ))

        return result

    def get_dominant_sentiment(self) -> tuple:
        """Obtener sentimiento dominante (excluyendo UNKNOWN)"""
        # Filtrar UNKNOWN
        non_unknown = self.sentiment_counts[self.sentiment_counts.index != 'UNKNOWN']

        if len(non_unknown) == 0:
            return "UNKNOWN", 0.0

        dominant = non_unknown.idxmax()
        count = non_unknown[dominant]
        percentage = (count / self.known_count) * 100 if self.known_count > 0 else 0

        return dominant, round(percentage, 2)

    def get_samples(self, limit_per_sentiment: int = 3) -> Dict[str, List[str]]:
        """Obtener ejemplos de textos por sentimiento"""
        samples = {}

        for sentiment in self.sentiment_counts.index:
            sentiment_posts = self.df[self.df['sentiment'] == sentiment]

            # Filtrar textos no vacios
            texts = sentiment_posts[sentiment_posts['text'].notna()]['text'].values

            # Obtener muestras
            sample_texts = []
            for text in texts[:limit_per_sentiment]:
                text_str = str(text).strip()
                # Limpiar HTML entities
                text_clean = text_str.replace('&nbsp;', ' ').replace('&nbsp', ' ')[:100]
                if text_clean:
                    sample_texts.append(text_clean)

            if sample_texts:
                samples[sentiment] = sample_texts

        return samples

    def analyze(self) -> SentimentResponse:
        """Realizar analisis completo de sentimientos"""
        distribution = self.get_distribution()
        dominant_sentiment, dominant_percentage = self.get_dominant_sentiment()
        samples = self.get_samples()

        cobertura = (self.known_count / self.total_records * 100) if self.total_records > 0 else 0

        return SentimentResponse(
            distribucion=distribution,
            sentimiento_dominante=dominant_sentiment,
            porcentaje_dominante=dominant_percentage,
            total_registros=self.total_records,
            desconocidos=self.unknown_count,
            cobertura=round(cobertura, 2),
            muestras_por_sentimiento=samples
        )


# ==============================================================================
# FASTAPI APP
# ==============================================================================

app = FastAPI(
    title="Sentiment MCP",
    description="Analiza los sentimientos en conversaciones digitales",
    version="1.0.0"
)

# Inicializar analyzer
loader = get_loader()
analyzer = SentimentAnalyzer(loader.df)
cache = {}


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "Sentiment MCP",
        "port": config.SENTIMENT_MCP_PORT
    }


@app.get("/analisis/sentimiento", response_model=SentimentResponse)
async def get_sentiment_analysis():
    """
    Obtener analisis de sentimientos del dataset

    Returns:
        SentimentResponse con:
        - Distribucion de sentimientos
        - Sentimiento dominante
        - Muestras de textos por sentimiento
    """
    cache_key = "sentimiento_global"

    # Verificar cache
    if cache_key in cache:
        return cache[cache_key]

    try:
        result = analyzer.analyze()
        cache[cache_key] = result
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en analisis: {str(e)}")


@app.get("/analisis/sentimiento/distribucion")
async def get_sentiment_distribution():
    """Obtener distribucion de sentimientos"""
    try:
        distribution = analyzer.get_distribution()
        return {"distribucion": distribution}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analisis/sentimiento/dominante")
async def get_dominant_sentiment():
    """Obtener sentimiento dominante"""
    try:
        dominant, percentage = analyzer.get_dominant_sentiment()
        return {
            "sentimiento_dominante": dominant,
            "porcentaje": percentage
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
    print(f"\n[STARTING] Sentiment MCP on port {config.SENTIMENT_MCP_PORT}")
    print(f"[INFO] Dataset: {loader.get_stats()['rows']} rows loaded")
    print(f"[INFO] Sentiment distribution precalculated")
    print(f"\n[READY] Sentiment MCP listening on http://localhost:{config.SENTIMENT_MCP_PORT}")
    print(f"[READY] API docs at http://localhost:{config.SENTIMENT_MCP_PORT}/docs\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.SENTIMENT_MCP_PORT,
        log_level="info"
    )
