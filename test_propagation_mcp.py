"""
Test del Propagation MCP

Uso:
  Terminal 1: python -m services.propagation_mcp.main
  Terminal 2: python test_propagation_mcp.py
"""

import requests
import json
import time

BASE_URL = "http://localhost:8003"

def test_propagation_mcp():
    """Test del Propagation MCP"""
    print("\n" + "=" * 80)
    print("TEST - PROPAGATION MCP")
    print("=" * 80)

    # Test 1: Health check
    print("\n[Test 1] Health check")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"  Status: {resp.status_code}")
        data = resp.json()
        print(f"  Dataset: {data['dataset']['rows']} rows")
        print(f"  [OK] MCP is running")
    except Exception as e:
        print(f"  [FAIL] {e}")
        print(f"  Make sure to start the MCP first:")
        print(f"    python -m services.propagation_mcp.main")
        return

    # Test 2: Analizar un post aleatorio con parentId
    print("\n[Test 2] Obtener posts para analizar")
    try:
        from shared import get_loader
        loader = get_loader()
        df = loader.df

        # Encontrar un post con parentId (es decir, que es una respuesta)
        posts_with_children = df[df['id'].isin(df['parentId'].dropna().unique())]

        if len(posts_with_children) > 0:
            test_post = posts_with_children.iloc[0]
            post_id = test_post['id']
            post_text = str(test_post.get('text', ''))[:100]

            print(f"  Post encontrado: {post_id}")
            print(f"  Texto: {post_text}...")
        else:
            print("  [WARN] No se encontraron posts con respuestas")
            print("  Usando el primer post del dataset")
            test_post = df.iloc[0]
            post_id = test_post['id']

    except Exception as e:
        print(f"  [FAIL] {e}")
        return

    # Test 3: Llamar al endpoint de propagacion
    print(f"\n[Test 3] Analizar propagacion del post: {post_id}")
    try:
        start = time.time()
        resp = requests.get(
            f"{BASE_URL}/analisis/propagacion",
            params={"post_id": post_id},
            timeout=10
        )
        elapsed = time.time() - start

        print(f"  Status: {resp.status_code}")
        print(f"  Tiempo: {elapsed:.2f} segundos")

        if resp.status_code == 200:
            data = resp.json()
            print(f"\n  [OK] Propagacion analizada:")
            print(f"    - Alcance total: {data['alcance_total']} respuestas")
            print(f"    - Hijos directos: {data['hijos_directos']}")
            print(f"    - Profundidad maxima: {data['profundidad_maxima']}")
            print(f"    - Velocidad media: {data['velocidad_media_minutos']} minutos")
            print(f"    - Duracion total: {data['duracion_total_horas']} horas")
            print(f"    - Timestamp original: {data['timestamp_original']}")
            print(f"    - Distribucion por nivel: {data['distribucion_por_nivel']}")
            print(f"    - Top autores: {list(data['top_autores_respuestas'].items())[:3]}")

        else:
            print(f"  [FAIL] Error {resp.status_code}")
            print(f"  {resp.text}")

    except Exception as e:
        print(f"  [FAIL] {e}")
        return

    # Test 4: Caché
    print(f"\n[Test 4] Verificar caché (segunda llamada debe ser mas rapida)")
    try:
        start = time.time()
        resp = requests.get(
            f"{BASE_URL}/analisis/propagacion",
            params={"post_id": post_id},
            timeout=10
        )
        elapsed = time.time() - start

        print(f"  Status: {resp.status_code}")
        print(f"  Tiempo (con cache): {elapsed:.2f} segundos")
        print(f"  [OK] Cache funcionando")

    except Exception as e:
        print(f"  [FAIL] {e}")

    print("\n" + "=" * 80)
    print("[OK] TESTS COMPLETADOS")
    print("=" * 80)


if __name__ == "__main__":
    test_propagation_mcp()
