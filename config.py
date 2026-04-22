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
