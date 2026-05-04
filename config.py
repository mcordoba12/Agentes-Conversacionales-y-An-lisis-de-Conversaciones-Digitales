"""
Configuración centralizada del proyecto
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Directorios
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = PROJECT_ROOT / "docs"

# Dataset
DATA_PATH = os.getenv("DATA_PATH", str(DATA_DIR / "Reto_data_20251023_122206.parquet"))

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY no está configurada. "
        "Copia .env.example a .env y agrega tu clave de API."
    )

# Model
LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE = 0.7

# LLM Provider (Phase 5 - Transfer Learning)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai | ollama

# Ollama settings (Phase 5 - Free local inference)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# MCP Ports
SENTIMENT_MCP_PORT = int(os.getenv("SENTIMENT_MCP_PORT", 8001))
INFLUENCE_MCP_PORT = int(os.getenv("INFLUENCE_MCP_PORT", 8002))
PROPAGATION_MCP_PORT = int(os.getenv("PROPAGATION_MCP_PORT", 8003))

# Agent
AGENT_MEMORY_WINDOW = 6  # Últimos N turnos en memoria

# URLs de MCPs (para el agente)
MCP_URLS = {
    "sentiment": f"http://localhost:{SENTIMENT_MCP_PORT}",
    "influence": f"http://localhost:{INFLUENCE_MCP_PORT}",
    "propagation": f"http://localhost:{PROPAGATION_MCP_PORT}",
}

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Security (Phase 1.5)
SECURITY_ENABLED = os.getenv("SECURITY_ENABLED", "true").lower() == "true"
SECURITY_AUDIT_ENABLED = os.getenv("SECURITY_AUDIT_ENABLED", "true").lower() == "true"
SECURITY_AUDIT_DB = os.getenv("SECURITY_AUDIT_DB", str(DATA_DIR / "audit.db"))
SECURITY_RATE_LIMITING_ENABLED = os.getenv("SECURITY_RATE_LIMITING_ENABLED", "true").lower() == "true"
SECURITY_MAX_REQUESTS_PER_MINUTE = int(os.getenv("SECURITY_MAX_REQUESTS_PER_MINUTE", "20"))

# FinOps (Phase 2)
FINOPS_ENABLED = os.getenv("FINOPS_ENABLED", "true").lower() == "true"
FINOPS_MONTHLY_QUERIES_ESTIMATE = int(os.getenv("FINOPS_MONTHLY_QUERIES_ESTIMATE", "300"))

# Long-Term Memory (Phase 3)
LT_MEMORY_ENABLED = os.getenv("LT_MEMORY_ENABLED", "true").lower() == "true"
LT_MEMORY_BACKEND = os.getenv("LT_MEMORY_BACKEND", "sqlite")  # sqlite | chroma | hybrid
LT_MEMORY_DB = os.getenv("LT_MEMORY_DB", str(DATA_DIR / "long_term_memory.db"))
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(DATA_DIR / "chroma_db"))
LT_MEMORY_TOP_K = int(os.getenv("LT_MEMORY_TOP_K", "3"))

# Observability (Phase 4)
OBS_ENABLED = os.getenv("OBS_ENABLED", "true").lower() == "true"
OBS_RAGAS_ENABLED = os.getenv("OBS_RAGAS_ENABLED", "true").lower() == "true"
