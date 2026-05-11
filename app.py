"""
FastAPI Web App for IA RETO Agent
Expone endpoints REST para despliegue cloud (Render, Railway, etc.)
Requiere: langchain-groq para Groq LLM support
"""

import os
import sys
import time
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Agregar proyecto al path
sys.path.insert(0, os.path.dirname(__file__))

from agent.graph import ConversationalAgent
import config


# ============================================================================
# FastAPI Setup
# ============================================================================

app = FastAPI(
    title="IA RETO - Conversational Agent API",
    description="Agent conversacional para análisis de conversaciones digitales",
    version="1.0.0",
)

# CORS para Streamlit Cloud + desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models
# ============================================================================

class QueryRequest(BaseModel):
    """Request para hacer una pregunta al agente"""
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Response del agente con respuesta + métricas"""
    response: str
    tokens_used: int
    cost: float
    latency_ms: float
    tool_used: str
    success: bool


class ResetResponse(BaseModel):
    """Response de reset"""
    status: str
    message: str


class MetricsResponse(BaseModel):
    """Métricas de la sesión"""
    total_queries: int
    session_cost: float
    avg_latency_ms: float
    total_tokens: int
    tool_distribution: dict
    success_rate: float


class HealthResponse(BaseModel):
    """Health check"""
    status: str
    provider: str
    timestamp: str


# ============================================================================
# Global Agent Instance
# ============================================================================

agent_init_error = None
try:
    agent = ConversationalAgent()
    agent_ready = True
except Exception as e:
    print(f"⚠️  Error inicializando agente: {e}")
    import traceback
    traceback.print_exc()
    agent_init_error = str(e)
    agent = None
    agent_ready = False


# ============================================================================
# Routes
# ============================================================================

@app.get("/", tags=["info"])
def root():
    """Info del API"""
    return {
        "name": "IA RETO Conversational Agent",
        "description": "Agent conversacional para análisis de conversaciones digitales",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "chat": "POST /chat",
            "reset": "POST /reset",
            "metrics": "GET /metrics",
            "docs": "GET /docs",
        },
        "provider": config.LLM_PROVIDER,
    }


@app.get("/health", response_model=dict, tags=["health"])
def health():
    """Health check del API"""
    from agent.llm_factory import get_provider_info
    provider_info = get_provider_info()

    response = {
        "status": "ready" if agent_ready else "not_ready",
        "provider": provider_info.get("provider", "unknown"),
        "timestamp": datetime.now().isoformat(),
    }

    if agent_init_error:
        response["error"] = agent_init_error

    return response


@app.post("/chat", response_model=QueryResponse, tags=["chat"])
def chat(request: QueryRequest):
    """
    Procesa una pregunta y retorna la respuesta del agente

    Args:
        query: La pregunta del usuario
        session_id: ID de sesión (opcional)

    Returns:
        Respuesta con métricas
    """
    if not agent_ready:
        raise HTTPException(
            status_code=503,
            detail="Agente no inicializado. Revisa los logs."
        )

    if not request.query or len(request.query.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="La query no puede estar vacía"
        )

    try:
        start_time = time.time()

        # Llamar al agente
        response, metadata = agent.chat(request.query)

        latency_ms = (time.time() - start_time) * 1000

        return QueryResponse(
            response=response,
            tokens_used=metadata.get("total_tokens", 0),
            cost=metadata.get("total_cost", 0),
            latency_ms=latency_ms,
            tool_used=metadata.get("tool_used", "unknown"),
            success=True,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando query: {str(e)}"
        )


@app.post("/reset", response_model=ResetResponse, tags=["agent"])
def reset_agent():
    """Reinicia el estado del agente"""
    if not agent_ready:
        raise HTTPException(
            status_code=503,
            detail="Agente no inicializado"
        )

    try:
        agent.reset()
        return ResetResponse(
            status="success",
            message="Agente reiniciado exitosamente"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reiniciando agente: {str(e)}"
        )


@app.get("/metrics", response_model=MetricsResponse, tags=["metrics"])
def get_metrics():
    """Retorna métricas de la sesión actual"""
    if not agent_ready:
        raise HTTPException(
            status_code=503,
            detail="Agente no inicializado"
        )

    try:
        metrics = agent.get_metrics_report()

        return MetricsResponse(
            total_queries=metrics.get("total_queries", 0),
            session_cost=metrics.get("session_cost", 0),
            avg_latency_ms=metrics.get("avg_latency_ms", 0),
            total_tokens=metrics.get("total_tokens", 0),
            tool_distribution=metrics.get("tool_distribution", {}),
            success_rate=metrics.get("success_rate", 0),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo métricas: {str(e)}"
        )


# ============================================================================
# CLI Helper
# ============================================================================

def print_startup_banner():
    """Banner de inicio"""
    from agent.llm_factory import get_provider_info

    provider_info = get_provider_info()
    provider = provider_info.get("provider", "unknown")

    print("\n" + "="*70)
    print("🚀 IA RETO - Conversational Agent API")
    print("="*70)
    print(f"LLM Provider: {provider}")
    print(f"Status: {'✅ Ready' if agent_ready else '❌ Error'}")
    print("\n📚 API Documentation:")
    print("   http://localhost:8000/docs")
    print("\n💬 Chat Endpoint:")
    print("   POST http://localhost:8000/chat")
    print("   Body: {\"query\": \"¿Cuál es el sentimiento principal?\"}")
    print("\n📊 Metrics Endpoint:")
    print("   GET http://localhost:8000/metrics")
    print("\n🔄 Reset Endpoint:")
    print("   POST http://localhost:8000/reset")
    print("="*70 + "\n")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print_startup_banner()

    # Port desde env var o default 8000
    port = int(os.getenv("PORT", 8000))

    # Run
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
