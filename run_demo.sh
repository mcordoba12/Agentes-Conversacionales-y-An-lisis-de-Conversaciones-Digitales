#!/bin/bash

# Run Complete Demo: MCPs + Agent Service + Dashboard
# Usage: bash run_demo.sh

set -e

echo "================================================================================"
echo "🤖 AGENTE CONVERSACIONAL - DEMO SETUP"
echo "================================================================================"
echo ""
echo "This script will start:"
echo "  1. 3 MCPs (FastAPI services on ports 8001-8003)"
echo "  2. Agent Service (FastAPI on port 8000)"
echo "  3. Dashboard (Streamlit on port 8501)"
echo ""
echo "You will need 4 terminals:"
echo "  - Terminal 1: MCPs"
echo "  - Terminal 2: Agent Service"
echo "  - Terminal 3: Dashboard"
echo "  - Terminal 4: Chat/Interact"
echo ""
echo "Starting..."
echo ""

# Función para limpiar procesos al salir
cleanup() {
    echo ""
    echo "Stopping services..."
    pkill -f "sentiment_mcp" || true
    pkill -f "influence_mcp" || true
    pkill -f "propagation_mcp" || true
    pkill -f "agent_service.py" || true
    pkill -f "streamlit" || true
}

trap cleanup EXIT

# Terminal 1: MCPs
echo "[Terminal 1] Starting MCPs..."
echo "  python -m services.sentiment_mcp.main"
echo "  python -m services.influence_mcp.main"
echo "  python -m services.propagation_mcp.main"
echo ""

if command -v tmux &> /dev/null; then
    # Usar tmux si está disponible
    tmux new-session -d -s mcps "python -m services.sentiment_mcp.main"
    sleep 2
    tmux new-window -t mcps -n "influence" "python -m services.influence_mcp.main"
    sleep 2
    tmux new-window -t mcps -n "propagation" "python -m services.propagation_mcp.main"
    echo "[OK] MCPs running in tmux session 'mcps'"
    echo "     View: tmux attach -t mcps"
    echo ""
else
    # Fallback: ejecutar en background
    python -m services.sentiment_mcp.main &
    echo "[OK] Sentiment MCP running (PID: $!)"
    sleep 1

    python -m services.influence_mcp.main &
    echo "[OK] Influence MCP running (PID: $!)"
    sleep 1

    python -m services.propagation_mcp.main &
    echo "[OK] Propagation MCP running (PID: $!)"
    echo ""
fi

# Terminal 2: Agent Service
echo "[Terminal 2] Starting Agent Service..."
echo "  python agent_service.py"
echo ""

if command -v tmux &> /dev/null; then
    tmux new-session -d -s agent "python agent_service.py"
    echo "[OK] Agent Service running in tmux"
    echo "     View: tmux attach -t agent"
else
    python agent_service.py &
    AGENT_PID=$!
    echo "[OK] Agent Service running (PID: $AGENT_PID)"
fi

sleep 2

echo ""
echo "[Terminal 3] Starting Dashboard..."
echo "  streamlit run dashboard/app.py"
echo ""

# Terminal 3: Dashboard
if command -v tmux &> /dev/null; then
    tmux new-session -d -s dashboard "streamlit run dashboard/app.py --logger.level=error"
    echo "[OK] Dashboard running in tmux"
    echo "     View: http://localhost:8501"
    echo "     Or:   tmux attach -t dashboard"
else
    streamlit run dashboard/app.py --logger.level=error &
    DASHBOARD_PID=$!
    echo "[OK] Dashboard running (PID: $DASHBOARD_PID)"
    echo "     View: http://localhost:8501"
fi

echo ""
echo "================================================================================"
echo "✅ All services started!"
echo "================================================================================"
echo ""
echo "Status:"
echo "  MCPs:           http://localhost:8001, 8002, 8003"
echo "  Agent Service:  http://localhost:8000"
echo "  Dashboard:      http://localhost:8501  ← OPEN THIS IN BROWSER"
echo ""
echo "Next steps:"
echo "  1. Open browser: http://localhost:8501"
echo "  2. Wait for 'Agent Service Connected' message"
echo "  3. Ask a question in the chat!"
echo ""
echo "To stop all services: Press Ctrl+C or run:"
echo "  pkill -f 'sentiment_mcp|influence_mcp|propagation_mcp|agent_service|streamlit'"
echo ""

# Mantener script abierto
wait
