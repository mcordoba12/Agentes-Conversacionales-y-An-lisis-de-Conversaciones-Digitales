@echo off
REM Run Complete Demo: MCPs + Agent Service + Dashboard
REM For Windows

echo ================================================================================
echo 🤖 AGENTE CONVERSACIONAL - DEMO SETUP (Windows)
echo ================================================================================
echo.
echo This script will start services. You need 4 command prompts:
echo.
echo   Prompt 1: MCPs (this one will open 3 terminals)
echo   Prompt 2: Agent Service
echo   Prompt 3: Dashboard
echo   Prompt 4: Interactive
echo.
echo Prerequisites:
echo   - All MCPs must be running (ports 8001-8003)
echo   - Agent Service runs on port 8000
echo   - Dashboard runs on port 8501
echo.

REM MCPs in separate windows
echo Starting MCPs...
echo.

start "Sentiment MCP (8001)" cmd /k "python -m services.sentiment_mcp.main"
timeout /t 2 /nobreak

start "Influence MCP (8002)" cmd /k "python -m services.influence_mcp.main"
timeout /t 2 /nobreak

start "Propagation MCP (8003)" cmd /k "python -m services.propagation_mcp.main"
timeout /t 2 /nobreak

echo.
echo ================================================================================
echo MCPs started in 3 separate windows
echo.
echo Now open 2 MORE command prompts and run:
echo.
echo   Prompt 2: python agent_service.py
echo   Prompt 3: streamlit run dashboard/app.py
echo.
echo Then open browser: http://localhost:8501
echo ================================================================================
echo.

pause
