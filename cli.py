"""
CLI Interface for Conversational Agent
Interfaz de terminal para interactuar con el agente
"""

import sys
from pathlib import Path

# Agregar proyecto al path
sys.path.insert(0, str(Path(__file__).parent))

from agent.graph import ConversationalAgent
from shared import get_loader
import config


# ==============================================================================
# INTERFAZ
# ==============================================================================

WELCOME_MESSAGE = """
================================================================================
AGENTE CONVERSACIONAL - ANALISIS DE CONVERSACIONES DIGITALES
================================================================================

Bienvenido. Soy un agente que analiza conversaciones digitales.

Puedo ayudarte con:
- Analizar la propagacion de mensajes
- Identificar usuarios influyentes
- Evaluar el sentimiento de las conversaciones

Ejemplos de preguntas:
  "¿Quiénes son los usuarios más influyentes?"
  "¿Cómo se propagó el mensaje con ID abc123?"
  "¿Cuál es el sentimiento general de las conversaciones?"
  "¿Quién escribió el post más comentado?"

Comandos:
  exit      - Salir
  reset     - Nueva conversacion
  help      - Mostrar este mensaje
  history   - Ver historial
  provider  - Ver/cambiar proveedor de LLM (Phase 5)
  costs     - Mostrar análisis de costos y tokens (FinOps)
  memory    - Ver estadísticas de memoria long-term
  memclear  - Limpiar memoria de esta sesión
  metrics   - Ver métricas de rendimiento (Observability)
  eval      - Ver evaluación de calidad (Ragas)
  dashboard - Abrir: streamlit run dashboard/app.py (Diferenciador)

================================================================================
"""

HELP_MESSAGE = """
Comandos disponibles:
  exit            - Salir del programa
  reset           - Iniciar nueva conversacion
  help            - Mostrar este mensaje
  history         - Ver historial de conversacion
  provider        - Ver proveedor LLM actual y cómo cambiar (Phase 5)
  costs           - Mostrar análisis de costos y tokens (FinOps)
  memory          - Ver estadísticas de memoria long-term
  memclear        - Limpiar memoria de esta sesión
  metrics         - Ver métricas de rendimiento (latencias, tool distribution)
  eval            - Ver evaluación de calidad de respuestas (Ragas)

Tipos de preguntas que puedes hacer:
  Propagacion:    "¿Cómo se propagó el post XYZ?"
  Influencia:     "¿Quiénes son los más influyentes?"
  Sentimientos:   "¿Cuál es el clima de la conversación?"
  Combinadas:     "¿El post más comentado tiene sentimiento positivo?"
"""


def format_response(response: str, color: bool = True) -> str:
    """Formatear respuesta del agente"""
    if color:
        return f"\nAgent: {response}\n"
    return response


def print_section(title: str):
    """Imprimir un titulo de seccion"""
    print(f"\n{'='*80}")
    print(f"{title:^80}")
    print(f"{'='*80}\n")


def main():
    """Funcion principal - loop de conversacion"""

    print(WELCOME_MESSAGE)

    # Verificar que los MCPs esten disponibles
    print("[Iniciando...] Verificando servidores MCP...")
    try:
        import requests
        for service_name, url in config.MCP_URLS.items():
            try:
                resp = requests.get(f"{url}/", timeout=2)
                if resp.status_code == 200:
                    print(f"  [OK] {service_name.upper():20} en {url}")
                else:
                    print(f"  [WARN] {service_name.upper():20} respondiendo con {resp.status_code}")
            except:
                print(f"  [ERROR] {service_name.upper():20} NO DISPONIBLE - Iniciar con:")
                if service_name == "sentiment":
                    print(f"         python -m services.sentiment_mcp.main")
                elif service_name == "influence":
                    print(f"         python -m services.influence_mcp.main")
                elif service_name == "propagation":
                    print(f"         python -m services.propagation_mcp.main")
    except Exception as e:
        print(f"  [ERROR] No se pudo verificar MCPs: {e}")

    # Cargar datos
    print("\n[Iniciando...] Cargando dataset...")
    try:
        loader = get_loader()
        stats = loader.get_stats()
        print(f"  [OK] Dataset: {stats['rows']} registros cargados")
    except Exception as e:
        print(f"  [ERROR] No se pudo cargar dataset: {e}")
        sys.exit(1)

    # Crear agente
    print("[Iniciando...] Inicializando agente...")
    try:
        agent = ConversationalAgent()
        print(f"  [OK] Agente listo\n")
    except Exception as e:
        print(f"  [ERROR] No se pudo inicializar agente: {e}")
        sys.exit(1)

    # Loop principal
    print("Escribe tu pregunta (o 'help' para ayuda):\n")

    turn_count = 0
    while True:
        try:
            # Prompt del usuario
            try:
                user_input = input("You: ").strip()
            except EOFError:
                # Ctrl+D en Linux/Mac o Ctrl+Z en Windows
                print("\n[Saliendo...]")
                break

            if not user_input:
                continue

            # Procesar comandos
            if user_input.lower() == "exit":
                print("[Saliendo...] Hasta luego!")
                break

            elif user_input.lower() == "reset":
                agent.reset()
                print("[Conversación reseteada. Empecemos de nuevo.]\n")
                continue

            elif user_input.lower() == "help":
                print(HELP_MESSAGE)
                continue

            elif user_input.lower() == "provider":
                from agent.llm_factory import get_provider_info
                info = get_provider_info()
                print("\n" + "="*80)
                print("LLM PROVIDER CONFIGURATION (Phase 5)")
                print("="*80)
                print(f"Provider:  {info.get('provider', 'unknown').upper()}")
                print(f"Model:     {info.get('model', 'unknown')}")
                print(f"Temp:      {info.get('temperature', 0.7)}")
                print(f"Cost Input:  {info.get('cost_input', 'N/A')}")
                print(f"Cost Output: {info.get('cost_output', 'N/A')}")

                if info.get('provider') == 'ollama':
                    print(f"URL:       {info.get('base_url', 'N/A')}")

                print("\nTo switch providers:")
                print("  1. Edit .env file:")
                if info.get('provider') == 'openai':
                    print("     LLM_PROVIDER=ollama")
                else:
                    print("     LLM_PROVIDER=openai")
                print("  2. Restart the agent\n")

                if info.get('provider') == 'openai':
                    print("To use Ollama (FREE, local):")
                    print("  1. Install: https://ollama.com")
                    print("  2. Run: ollama pull llama3.1:8b")
                    print("  3. Set LLM_PROVIDER=ollama in .env")
                    print("  4. Restart the agent\n")
                else:
                    print("Using Ollama (local, free). Current setup:")
                    print("  Make sure Ollama is running: ollama serve")
                    print("  To switch back to OpenAI: LLM_PROVIDER=openai\n")

                print("="*80 + "\n")
                continue

            elif user_input.lower().startswith("mode"):
                parts = user_input.split()
                if len(parts) < 2:
                    print("\nUSO: mode <patrón>")
                    print("Patrones disponibles: react, reflection, planning, hitl, default")
                    print("\nEjemplos:")
                    print("  mode react      → Razonamiento explícito (Thought/Action/Observation)")
                    print("  mode reflection → Auto-evaluación de respuestas")
                    print("  mode planning   → Descomposición de queries complejas")
                    print("  mode hitl       → Confirmación manual antes de ejecutar tools")
                    print("  mode default    → Volver al modo normal")
                    continue

                pattern = parts[1].lower()
                if pattern == "default":
                    agent.set_pattern_mode(None)
                    print("[Pattern] Modo normal activado")
                elif pattern in ["react", "reflection", "planning", "hitl"]:
                    agent.set_pattern_mode(pattern)
                    print(f"[Pattern] Patrón '{pattern}' activado")
                else:
                    print(f"[ERROR] Patrón desconocido: {pattern}")
                    print("Válidos: react, reflection, planning, hitl, default")
                continue

            elif user_input.lower() == "history":
                history = agent.get_conversation_history()
                if history:
                    print("\n" + "="*80)
                    print("HISTORIAL DE CONVERSACION")
                    print("="*80)
                    print(history)
                    print("="*80 + "\n")
                else:
                    print("[No hay historial aun]\n")
                continue

            elif user_input.lower() == "costs":
                report = agent.get_cost_report()
                print(report)
                continue

            elif user_input.lower() == "memory":
                stats = agent.get_memory_stats()
                print(stats)
                continue

            elif user_input.lower() == "memclear":
                result = agent.clear_long_term_memory(session_only=True)
                print(f"[Memory] {result}")
                continue

            elif user_input.lower() == "metrics":
                report = agent.get_metrics_report()
                print(report)
                continue

            elif user_input.lower() == "eval":
                report = agent.get_eval_report()
                print(report)
                continue

            # Procesar pregunta del usuario
            print("\n[Procesando...]")

            try:
                response = agent.chat(user_input)
                print(format_response(response))

                # FinOps: Mostrar línea de costo (Phase 2)
                if config.FINOPS_ENABLED and agent.cost_tracker:
                    tokens = agent.last_query_tokens
                    q_cost = agent.cost_tracker.get_query_cost(tokens["input"], tokens["output"])
                    s_cost = agent.cost_tracker.session_cost
                    print(f"[Cost] Query: ${q_cost:.4f} | Session: ${s_cost:.4f} | Tokens: {tokens['total']}")

                turn_count += 1

                # Mostrar tip cada 3 turnos
                if turn_count % 3 == 0:
                    print("[TIP] Usa 'history' para ver el contexto de la conversacion")
                    print("[TIP] Usa 'reset' para empezar una nueva conversacion\n")

            except Exception as e:
                print(f"\n[ERROR] Error procesando pregunta: {e}\n")
                import traceback
                traceback.print_exc()

        except KeyboardInterrupt:
            print("\n\n[Saliendo...] Hasta luego!")
            break

        except Exception as e:
            print(f"\n[ERROR] Error inesperado: {e}\n")


if __name__ == "__main__":
    main()
