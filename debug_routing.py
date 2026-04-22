"""
Debug: Verificar qué está pasando en el routing
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from agent.graph import detect_metrics_intent, detect_sentiment_intent
from langchain_core.messages import HumanMessage
import requests
import json

print("\n" + "="*80)
print("DEBUG: ROUTING DE METRICAS")
print("="*80)

# Test 1: Verificar detección
test_message = "¿Quién escribió el post más comentado?"

print(f"\n1. DETECCION DE INTENCION")
print(f"   Mensaje: '{test_message}'")

is_metrics = detect_metrics_intent(test_message)
is_sentiment = detect_sentiment_intent(test_message)

print(f"   -> detect_metrics_intent(): {is_metrics}")
print(f"   -> detect_sentiment_intent(): {is_sentiment}")

if not is_metrics:
    print("\n   [ERROR] No detecta como métrica!")
else:
    print("\n   [OK] Detectado como métrica")

# Test 2: Verificar que MCPs estén disponibles
print(f"\n2. VERIFICACION DE MCPs")

mcps = {
    "sentiment": "http://localhost:8001/analisis/sentimiento",
    "influence": "http://localhost:8002/analisis/metricas",
    "propagation": "http://localhost:8003/analisis/propagacion?post_id=test"
}

for name, url in mcps.items():
    try:
        if name == "propagation":
            resp = requests.get(url, timeout=2)
        else:
            resp = requests.get(url.split("?")[0], timeout=2)

        status = f"[OK] {resp.status_code}"
        print(f"   {name:15} {status}")
    except requests.exceptions.ConnectionError:
        print(f"   {name:15} [ERROR] No responde - esta corriendo?")
    except Exception as e:
        print(f"   {name:15} [ERROR] {str(e)[:40]}")

# Test 3: Simular llamada a MCP de influencia
print(f"\n3. LLAMADA AL MCP DE INFLUENCIA")

try:
    resp = requests.get("http://localhost:8002/analisis/metricas", timeout=5)

    if resp.status_code == 200:
        data = resp.json()
        print(f"   [OK] MCP retorno datos")
        print(f"   - Top autores: {len(data.get('top_autores_por_influencia', []))} items")
        print(f"   - Top posts: {len(data.get('top_posts_comentados', []))} items")

        if data.get('top_posts_comentados'):
            top_post = data['top_posts_comentados'][0]
            print(f"\n   POST MAS COMENTADO:")
            print(f"   - ID: {top_post.get('post_id')}")
            print(f"   - Autor: {top_post.get('autor')}")
            print(f"   - Respuestas: {top_post.get('cantidad_respuestas')}")
    else:
        print(f"   [ERROR] MCP retorno error: {resp.status_code}")
        print(f"   Response: {resp.text[:200]}")

except requests.exceptions.ConnectionError:
    print(f"   [ERROR] NO PUEDE CONECTAR A http://localhost:8002")
    print(f"      Esta corriendo el MCP de influencia?")
    print(f"\n   PARA INICIAR:")
    print(f"      python -m services.influence_mcp.main")
except Exception as e:
    print(f"   [ERROR] {e}")

print("\n" + "="*80)
print("DIAGNOSTICO")
print("="*80)

print("""
Si ves:
  ✓ detect_metrics_intent() = True
  ✓ MCP respondiendo [OK] 200
  ✓ Datos en POST MAS COMENTADO

Pero el agente SIGUE respondiendo genéricamente, el problema es:
  1. El agente no está llamando al MCP correctamente
  2. Hay un error en node_execute_tool()
  3. Hay un error en node_generate_response()

Si ves:
  ❌ [ERROR] No responde

El problema es:
  1. Los MCPs no están corriendo
  2. Los puertos están mal configurados
  3. El servidor está bloqueado

SIGUIENTE PASO:
  1. Inicia los MCPs:
     Terminal 1: python -m services.sentiment_mcp.main
     Terminal 2: python -m services.influence_mcp.main
     Terminal 3: python -m services.propagation_mcp.main

  2. Luego ejecuta este script de nuevo

  3. Si todo está OK aquí pero falla en el agente,
     hay un bug en el flujo del agente que necesita debugging adicional
""")

print("="*80 + "\n")
