# Agente Conversacional con Microservicios de Análisis - ICESI Reto

Conversational agent con 3 microservicios analíticos (MCPs) que permiten hacer análisis de conversaciones digitales en lenguaje natural.

## 🏗️ Arquitectura

- **3 Microservicios FastAPI** independientes:
  - 📊 Sentiment MCP (puerto 8001)
  - ⭐ Influence Metrics MCP (puerto 8002)
  - 🌳 Propagation MCP (puerto 8003)

- **Agente Conversacional** con LangGraph
  - Tool calling automático
  - Memory buffer (últimos 6 turnos)
  - Routing inteligente de herramientas

- **Data Layer** con Singleton DataLoader
  - Parquet cargado en RAM
  - Caché centralizado

## 📋 Prerequisitos

- Python 3.10+
- pip

## 🚀 Instalación

### 1. Clonar/Descargar el proyecto
```bash
cd "C:\Users\Angela\Documents\8 Octavo Semestre\IA 2\IA RETO"
```

### 2. Crear ambiente virtual (recomendado)
```bash
python -m venv venv
venv\Scripts\activate  # En Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
# Copiar el archivo de ejemplo
copy .env.example .env

# Editar .env y agregar tu OPENAI_API_KEY
# OPENAI_API_KEY=sk-...
```

## 📁 Estructura del Proyecto

```
IA RETO/
├── docs/
│   ├── arquitectura.mmd       # Diagrama Mermaid
│   ├── arquitectura.md        # Documentación
│   └── arquitectura.png       # Imagen de arquitectura
│
├── data/
│   └── Reto_data_20251023_122206.parquet
│
├── shared/
│   └── data_loader.py         # Singleton DataLoader
│
├── services/
│   ├── propagation_mcp/       # Análisis de propagación (obligatorio)
│   │   └── main.py
│   ├── influence_mcp/         # Análisis de influencia
│   │   └── main.py
│   └── sentiment_mcp/         # Análisis de sentimientos
│       └── main.py
│
├── agent/
│   ├── state.py               # Estado del agente (TypedDict)
│   ├── tools.py               # Definición de herramientas
│   ├── graph.py               # LangGraph StateGraph
│   └── memory.py              # Memory buffer
│
├── cli.py                     # Interfaz de línea de comandos
├── requirements.txt
├── .env.example
├── README.md
└── .gitignore
```

## ⚡ Inicio Rápido

### Opción A: Iniciar todo de una vez (recomendado)
```bash
# Se abre en múltiples terminales/procesos
python start_all.py
```

### Opción B: Iniciar servicios manualmente

**Terminal 1 - Sentiment MCP (Puerto 8001):**
```bash
python -m services.sentiment_mcp.main
```

**Terminal 2 - Influence MCP (Puerto 8002):**
```bash
python -m services.influence_mcp.main
```

**Terminal 3 - Propagation MCP (Puerto 8003):**
```bash
python -m services.propagation_mcp.main
```

**Terminal 4 - Agente Conversacional:**
```bash
python cli.py
```

## 💬 Ejemplo de Uso

Una vez el agente está corriendo:

```
Usuario: ¿Quiénes son los 5 usuarios más influyentes?
Agente: Llamando a Influence MCP... [resultado JSON] ... Los 5 usuarios más influyentes son...

Usuario: ¿Cómo se propagó el mensaje con ID 'abc123'?
Agente: Analizando propagación... [BFS en el árbol de replies] ... El mensaje tuvo un alcance de 43 respuestas...

Usuario: ¿Y qué sentimiento predomina en esas respuestas?
Agente: (Lee memoria del turno anterior) Analizando sentimiento del post abc123... El sentimiento dominante es NEGATIVO...
```

## 🔧 Configuración

Editar `.env` para cambiar:
- `OPENAI_API_KEY`: Tu clave de API de OpenAI
- Puertos de los MCPs (si hay conflictos)
- Ruta del parquet

## 📊 Dataset

- **Archivo**: `Reto_data_20251023_122206.parquet`
- **Registros**: 4,795 conversaciones
- **Campos clave**: `id`, `parentId`, `threadId`, `text`, `sentiment`, `influenceScore`, `author`, `createdAt`

## 🧪 Testing

### Test del DataLoader
```bash
python -c "from shared import get_loader; loader = get_loader(); print(loader.get_stats())"
```

### Test de un MCP específico
```bash
# Sentiment
curl "http://localhost:8001/analisis/sentimiento"

# Influence
curl "http://localhost:8002/analisis/metricas"

# Propagation
curl "http://localhost:8003/analisis/propagacion?post_id=c6adb4630994bdee807d387382d526bc"
```

## 🎯 Análisis Disponibles

### 1. Propagation MCP (OBLIGATORIO) 🌳
- Analiza cómo se propaga un mensaje en la red
- Métrica: Alcance, velocidad, profundidad del árbol
- Endpoint: `GET /analisis/propagacion?post_id=XXX`
- **Costo**: $0 (procesamiento determinístico con BFS)

### 2. Influence Metrics MCP ⭐
- Identifica usuarios influyentes
- Métrica: Top autores por influenceScore
- Endpoint: `GET /analisis/metricas`
- **Costo**: $0 (Pandas groupby)

### 3. Sentiment MCP 📊
- Distribución de sentimientos
- Métrica: Sentiment distribution, dominante
- Endpoint: `GET /analisis/sentimiento`
- **Costo**: ~$0.001 (solo si pides narrativa)

## 💰 Estimación de Costos

| Análisis | LLM? | Costo/Consulta |
|----------|------|----------------|
| Propagation | ❌ | $0.00 |
| Influence | ❌ | $0.00 |
| Sentiment | ❌ | $0.00 |
| Agente Routing | ✅ | ~$0.002 |
| Agente Formatting | ✅ | ~$0.002 |
| **Total** | - | **~$0.004 USD** |

## 📚 Documentación Adicional

- Ver `docs/arquitectura.md` para arquitectura detallada
- Ver `.claude/plans/rustling-zooming-hearth.md` para plan de implementación

## 🤝 Contribuir

Este es un proyecto del Reto ICESI. Cambios principales están documentados en el plan.

## 📝 Notas

- El parquet se carga en RAM al iniciar (eficiencia)
- Los resultados de MCPs se cachean en RAM (sin TTL)
- La memoria del agente es de sesión (se pierde al cerrar)

---

**¿Preguntas?** Ver documentación en `docs/` o el plan de implementación en `.claude/plans/`
