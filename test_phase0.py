"""
Test para verificar que Phase 0 (Setup) fue completado correctamente
Ejecutar: python test_phase0.py
"""

import sys
from pathlib import Path

# Agregar el proyecto al path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("TEST FASE 0 - SETUP")
print("=" * 80)

# Test 1: Verificar estructura de carpetas
print("\n[OK] Test 1: Verificar estructura de carpetas")
required_dirs = [
    "data",
    "docs",
    "shared",
    "services",
    "services/propagation_mcp",
    "services/influence_mcp",
    "services/sentiment_mcp",
    "agent",
]

for dir_path in required_dirs:
    full_path = Path(__file__).parent / dir_path
    if full_path.exists():
        print(f"  [OK] {dir_path}")
    else:
        print(f"  [FAIL] {dir_path} - FALTA")

# Test 2: Verificar archivos principales
print("\n[OK] Test 2: Verificar archivos principales")
required_files = [
    "requirements.txt",
    ".env.example",
    "config.py",
    "README.md",
    "shared/data_loader.py",
    "docs/arquitectura.mmd",
    "docs/arquitectura.md",
    "docs/arquitectura.png",
]

for file_path in required_files:
    full_path = Path(__file__).parent / file_path
    if full_path.exists():
        size = full_path.stat().st_size
        print(f"  [OK] {file_path} ({size} bytes)")
    else:
        print(f"  [FAIL] {file_path} - FALTA")

# Test 3: Verificar DataLoader
print("\n[OK] Test 3: Probar DataLoader Singleton")
try:
    from shared import get_loader
    loader = get_loader()
    stats = loader.get_stats()
    print(f"  [OK] DataLoader inicializado")
    print(f"    - Rows: {stats['rows']}")
    print(f"    - Columns: {stats['columns']}")
    print(f"    - Memory: {stats['memory_mb']:.2f} MB")
    print(f"    - Cache entries: {stats['cache_entries']}")
except Exception as e:
    print(f"  [FAIL] Error al inicializar DataLoader: {e}")

# Test 4: Verificar config
print("\n[OK] Test 4: Probar configuracion")
try:
    import config
    print(f"  [OK] config.py importado correctamente")
    print(f"    - DATA_PATH: {config.DATA_PATH}")
    print(f"    - LLM_MODEL: {config.LLM_MODEL}")
    print(f"    - SENTIMENT_MCP_PORT: {config.SENTIMENT_MCP_PORT}")
    print(f"    - INFLUENCE_MCP_PORT: {config.INFLUENCE_MCP_PORT}")
    print(f"    - PROPAGATION_MCP_PORT: {config.PROPAGATION_MCP_PORT}")
except Exception as e:
    print(f"  [FAIL] Error en config: {e}")

# Test 5: Verificar dependencias basicas
print("\n[OK] Test 5: Verificar dependencias instaladas")
dependencies = [
    ("pandas", "pd"),
    ("fastapi", "fastapi"),
    ("pydantic", "pydantic"),
    ("langchain", "langchain"),
    ("langgraph", "langgraph"),
    ("openai", "openai"),
    ("dotenv", "dotenv"),
]

for pkg_name, import_name in dependencies:
    try:
        __import__(import_name)
        print(f"  [OK] {pkg_name}")
    except ImportError:
        print(f"  [FAIL] {pkg_name} - NO INSTALADO (ejecuta: pip install -r requirements.txt)")

print("\n" + "=" * 80)
print("[OK] FASE 0 COMPLETADA")
print("=" * 80)
print("\nPróximos pasos:")
print("1. Crear .env con tu OPENAI_API_KEY")
print("2. Comenzar Fase 1: Propagation MCP")
print("\nEjecuta: python cli.py (después de que todos los MCPs estén corriendo)")
