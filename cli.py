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
  exit     - Salir
  reset    - Nueva conversacion
  help     - Mostrar este mensaje
  history  - Ver historial

================================================================================
"""

HELP_MESSAGE = """
Comandos disponibles:
  exit            - Salir del programa
  reset           - Iniciar nueva conversacion
  help            - Mostrar este mensaje
  history         - Ver historial de conversacion

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

            # Procesar pregunta del usuario
            print("\n[Procesando...]")

            try:
                response = agent.chat(user_input)
                print(format_response(response))

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
