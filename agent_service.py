"""
FastAPI Service for Conversational Agent
Expone el agente como un servicio HTTP para que el dashboard pueda chatear sin terminal
"""

import sys
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Agregar proyecto al path
sys.path.insert(0, str(Path(__file__).parent))

from agent.graph import ConversationalAgent
from shared import get_loader
import config

# ==============================================================================
# MODELOS
# ==============================================================================

class ChatRequest(BaseModel):
    """Solicitud de chat"""
    question: str
    session_id: str = None


class ChatResponse(BaseModel):
    """Respuesta del agente"""
    response: str
    session_id: str
    tokens: Dict[str, int]
    cost: float
    latency_ms: float
    success: bool
    error: str = None


# ==============================================================================
# FASTAPI APP
# ==============================================================================

app = FastAPI(
    title="Agente Conversacional - Service",
    description="API para chatear con el agente (usado por Dashboard)",
    version="1.0"
)

# Estado global
agent: ConversationalAgent = None


# ==============================================================================
# STARTUP
# ==============================================================================

@app.on_event("startup")
async def startup():
    """Inicializar agente al arrancar el servicio"""
    global agent

    print("[Service] Inicializando agente...")

    try:
        # Cargar datos
        loader = get_loader()
        stats = loader.get_stats()
        print(f"  [OK] Dataset: {stats['rows']} registros cargados")
    except Exception as e:
        print(f"  [ERROR] No se pudo cargar dataset: {e}")
        raise

    try:
        # Crear agente
        agent = ConversationalAgent()
        print(f"  [OK] Agente listo\n")
    except Exception as e:
        print(f"  [ERROR] No se pudo inicializar agente: {e}")
        raise


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@app.get("/")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "service": "Agente Conversacional",
        "version": "1.0"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal: chatear con el agente

    Args:
        request: ChatRequest con la pregunta

    Returns:
        ChatResponse con la respuesta del agente y métricas
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agente no inicializado")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")

    try:
        # Ejecutar chat
        response = agent.chat(request.question)

        # Obtener métricas
        tokens = agent.last_query_tokens
        cost = agent.cost_tracker.get_query_cost(tokens["input"], tokens["output"]) if agent.cost_tracker else 0.0
        latency = agent.last_query_latency if hasattr(agent, 'last_query_latency') else 0.0
        session_id = agent.session_id

        return ChatResponse(
            response=response,
            session_id=session_id,
            tokens=tokens,
            cost=cost,
            latency_ms=latency,
            success=True
        )

    except Exception as e:
        print(f"[ERROR] Error en /chat: {e}")
        import traceback
        traceback.print_exc()

        return ChatResponse(
            response="",
            session_id=agent.session_id if agent else "unknown",
            tokens={"input": 0, "output": 0, "total": 0},
            cost=0.0,
            latency_ms=0.0,
            success=False,
            error=str(e)
        )


@app.get("/status")
async def status():
    """Obtener estado del agente"""
    if not agent:
        return {"status": "not_initialized"}

    return {
        "status": "ready",
        "session_id": agent.session_id,
        "pattern_mode": agent.state.get("pattern_mode"),
        "memory_size": len(agent.state.get("messages", [])),
        "cost_tracker_enabled": agent.cost_tracker is not None,
    }


@app.post("/reset")
async def reset_conversation():
    """Resetear la conversación"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agente no inicializado")

    agent.reset()
    return {"status": "reset", "session_id": agent.session_id}


@app.post("/mode/{pattern_name}")
async def set_pattern(pattern_name: str):
    """Cambiar patrón de ejecución (Phase 6)"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agente no inicializado")

    valid_patterns = ["react", "reflection", "planning", "hitl", "default"]
    if pattern_name not in valid_patterns:
        raise HTTPException(
            status_code=400,
            detail=f"Patrón inválido. Válidos: {', '.join(valid_patterns)}"
        )

    if pattern_name == "default":
        agent.set_pattern_mode(None)
    else:
        agent.set_pattern_mode(pattern_name)

    return {"status": "ok", "pattern": pattern_name}


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    import uvicorn

    print("""
================================================================================
AGENTE CONVERSACIONAL - SERVICE (FastAPI)
================================================================================

Iniciando servicio en http://localhost:8000

Endpoints disponibles:
  GET  /              → Health check
  GET  /status        → Estado del agente
  POST /chat          → Chatear con el agente
  POST /reset         → Resetear conversación
  POST /mode/{name}   → Cambiar patrón (react, reflection, planning, hitl)

Para usar con el dashboard:
  1. Abre esta terminal
  2. En otra terminal: streamlit run dashboard/app.py
  3. El dashboard hará requests a http://localhost:8000/chat

================================================================================
""")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
