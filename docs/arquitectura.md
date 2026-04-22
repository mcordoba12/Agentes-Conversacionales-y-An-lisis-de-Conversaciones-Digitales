# Arquitectura del Agente Conversacional - ICESI Reto

## Descripción General

Este documento describe la arquitectura de alto nivel del sistema de Agente Conversacional con Microservicios de Análisis (MCP) para el Reto de Ingeniería de IA de ICESI.

---

## Componentes Principales

### 1. **INTERFAZ - USUARIO** (Azul)
- **CLI Interface**: Terminal interactiva donde el usuario hace preguntas en lenguaje natural
- **Usuario Final**: Interactúa escribiendo preguntas como "¿Cómo se propagó el mensaje X?"
- Responsabilidad: Capturar entrada, mostrar salida de forma conversacional

### 2. **AGENTE CONVERSACIONAL** (Púrpura) - LangGraph
- **StateGraph**: Orquesta el flujo del agente
  - Recibe pregunta del usuario + contexto de memoria
  - Decide qué herramienta (tool) necesita llamar
  - Ejecuta llamadas HTTP a los MCPs
  - Formatea la respuesta final

- **Memory Buffer**: Almacena los últimos 6 turnos de conversación
  - Formato: `[{role: "user", content: "..."}, {role: "assistant", ...}]`
  - Permite que el agente entienda preguntas de seguimiento
  - Ejemplo: "¿y el sentimiento es positivo?" → agente obtiene el post_id del contexto previo

### 3. **MICROSERVICIOS MCP** (Verde) - FastAPI
Tres servicios independientes, cada uno en su propio puerto:

#### **MCP1 - Sentiment API (Puerto 8001)**
- `GET /analisis/sentimiento`
- Retorna: Distribución de sentimientos, sentimiento dominante, muestra de textos
- **Cero LLM**: Solo cuenta etiquetas existentes con `value_counts()`
- Caché: Resultados en RAM con hash de parámetros
- Datos: Accede a DataFrame del parquet vía DataLoader

#### **MCP2 - Influence Metrics API (Puerto 8002)**
- `GET /analisis/metricas`
- Retorna: Top autores por influenceScore, posts más comentados, ranking
- **Cero LLM**: Pandas groupby + sort puro
- Caché: Resultados en RAM
- Datos: Accede al parquet vía DataLoader

#### **MCP3 - Propagation API (Puerto 8003)** [OBLIGATORIO]
- `GET /analisis/propagacion?post_id=XXX`
- Retorna: Alcance (N hijos), velocidad media, profundidad del árbol, lista de hijos
- **Cero LLM**: BFS (Breadth-First Search) sobre parentId/threadId
- Caché: Resultados en RAM
- Datos: Accede al parquet vía DataLoader

**Principio clave**: MCPs NO llaman a LLM. Solo hacen procesamiento determinístico.

### 4. **CAPA DE DATOS** (Verde oscuro)
- **Singleton DataLoader**: Carga el parquet UNA SOLA VEZ al startup
  - Patrón Singleton: todos los MCPs comparten la misma instancia
  - Eficiencia: evita cargar 4,795 filas múltiples veces
  - Ubicación: `shared/data_loader.py`

- **Parquet Dataset**: Archivo con 4,795 conversaciones y 72 columnas
  - Campos clave: `id`, `parentId`, `threadId`, `sentiment`, `influenceScore`, `text`, `author`, `createdAt`
  - Se mantiene en RAM durante la sesión
  - Solo se carga una vez al iniciar los servicios

- **Cache RAM**: Cada MCP tiene su propio dict de caché
  - Clave: `hash(endpoint + parámetros)`
  - Valor: Resultado JSON
  - Sin TTL: Los resultados persisten durante la sesión (aceptable para demo)

### 5. **LLM - OpenAI** (Naranja)
- **Modelo**: GPT-4o-mini (costo optimizado)
- **Responsabilidades**:
  1. **Routing de tools**: Decide qué MCP llamar basado en la pregunta
  2. **Formatting de respuesta**: Convierte JSON de MCPs en texto conversacional
  3. **Enriquecimiento** (opcional): Solo si necesitas mejorar UNKNOWN en sentimientos

- **Costo**: ~$0.003-0.005 USD por consulta completa
  - Routing: 1 call LLM (tokens bajos)
  - Formatting: 1 call LLM (tokens bajos con contexto)
  - Total: 2 calls LLM por pregunta del usuario

---

## Flujo de Ejecución Paso a Paso

### Caso 1: Pregunta Simple con Tool
```
Usuario: "¿Cuánto se propagó el post abc123?"
    ↓
CLI captura texto → Agente recibe
    ↓
Agente + Memory: "Veo que es sobre propagación"
    ↓
LLM (Router): "Necesito tool: trace_propagation(post_id='abc123')"
    ↓
HTTP GET http://localhost:8003/analisis/propagacion?post_id=abc123
    ↓
PropagationMCP:
  - Cache MISS → busca en parquet
  - BFS desde post_id sobre parentId
  - Calcula alcance, velocidad, árbol
  ↓
Retorna JSON: {id_original, alcance: 43, velocidad_media: "5 min", ...}
    ↓
Agente recibe JSON → actualiza Memory
    ↓
LLM (Formatter): Convierte JSON a respuesta natural
    ↓
Agente: "El post abc123 tuvo un alcance de 43 respuestas direc..."
    ↓
CLI muestra → Usuario ve respuesta
```

### Caso 2: Pregunta de Seguimiento (Usa Memoria)
```
Usuario: "¿Y qué sentimiento predomina?"
    ↓
Agente lee Memory (últimos 6 turnos) → Ve que hablamos del post abc123
    ↓
LLM + contexto de memoria: "Necesito tool: analyze_sentiment(post_id='abc123')"
    ↓
HTTP GET http://localhost:8001/analisis/sentimiento?post_id=abc123
    ↓
SentimentMCP:
  - Cache HIT o MISS
  - value_counts() de sentimientos en ese post
  ↓
Retorna JSON: {sentiment: "NEGATIVE", distribucion: {...}}
    ↓
Agente: "En el contexto del post anterior, el sentimiento es NEGATIVO..."
    ↓
Memory: Agrega este nuevo turno al buffer (mantiene últimos 6)
```

### Caso 3: Pregunta sin Tool (Solo Memoria)
```
Usuario: "¿Puedes resumir lo que analizaste?"
    ↓
Agente + Memory (histórico completo)
    ↓
LLM: "No necesito tool, tengo el contexto en memoria"
    ↓
LLM genera respuesta basada en Memory (una sola llamada)
    ↓
Costo: $0.001 (mínimo) porque reutilizamos memoria
```

---

## Decisiones Arquitectónicas Clave

### 1. **MCPs Independientes (No Tool Calling entre MCPs)**
- Cada MCP es una FastAPI app independiente en su propio puerto
- Solo el Agente (LangGraph) orquesta entre MCPs
- Ventaja: Escalable, desacoplado, fácil de testear

### 2. **Cero LLM en MCPs**
- Propagación: BFS puro (procesamiento determinístico)
- Influencia: Pandas groupby (procesamiento determinístico)
- Sentimientos: value_counts() (etiquetas ya existen)
- LLM solo en el Agente para routing + formatting
- **Beneficio**: Costo ULTRA bajo (~$0.01-0.05 USD por demo completa)

### 3. **Memoria en RAM (Sesión)**
- Ventaja: Cero configuración de BD
- Desventaja: Se pierde al cerrar
- Para la demo: Perfecto (dura 15-30 minutos)
- Si necesitaras persistencia: Agregar SQLite con 1 tabla simple

### 4. **Singleton DataLoader**
- Carga parquet UNA sola vez
- Compartido por los 3 MCPs
- Evita triplicar uso de memoria
- Ubicación central: `shared/data_loader.py`

### 5. **LangGraph + StateGraph**
- Tool calling automático + manejo de estado
- Memory buffer integrado
- Routing basado en LLM
- **Bonus**: Puntos extra garantizados por usar framework avanzado

---

## Estructura de Carpetas

```
IA RETO/
├── docs/
│   ├── arquitectura.mmd          # Este diagrama
│   ├── arquitectura.md           # Esta documentación
│   └── arquitectura.png          # Imagen renderizada
│
├── data/
│   └── Reto_data_20251023_122206.parquet
│
├── shared/
│   └── data_loader.py            # Singleton para cargar parquet
│
├── services/
│   ├── propagation_mcp/
│   │   └── main.py               # FastAPI, Puerto 8003
│   ├── influence_mcp/
│   │   └── main.py               # FastAPI, Puerto 8002
│   └── sentiment_mcp/
│       └── main.py               # FastAPI, Puerto 8001
│
├── agent/
│   ├── state.py                  # AgentState TypedDict
│   ├── tools.py                  # Tool definitions + HTTP callers
│   ├── graph.py                  # LangGraph StateGraph
│   └── memory.py                 # Sliding window memory
│
├── cli.py                        # Entry point - Terminal interface
├── .env                          # OPENAI_API_KEY
├── requirements.txt
└── README.md
```

---

## Métricas de Optimización

| Aspecto | Estrategia | Costo | Beneficio |
|---------|-----------|-------|----------|
| **Parquet Loading** | Singleton + RAM | Mem+5MB | Carga 1 sola vez |
| **MCP Caching** | Dict RAM sin TTL | Mem+1MB | Evita recálculos |
| **LLM Calls** | Solo routing + formatting | $0.002/turno | Min necesario |
| **Sentiment** | Etiquetas existentes | $0 | 87% cobertura ya existe |
| **Propagation** | BFS determinístico | $0 | Cero LLM |
| **Influence** | Pandas determinístico | $0 | Cero LLM |
| **Memory** | Sliding window 6 turnos | Mem+50KB | Contexto sin contaminación |

**Total costo estimado para demo completa: ~$0.01-0.05 USD**

---

## Puntos Extra Garantizados

✨ **LangGraph** con StateGraph (vs simple tool calling)
✨ **Memory contextual** (los 6 últimos turnos + preguntas de seguimiento)
✨ **Tool Calling explícito** con definiciones de schema
✨ **Procesamiento determinístico** (Propagation + Influence sin LLM)

---

## Referencias Rápidas

- **Diagrama original**: `docs/arquitectura.mmd`
- **Plan detallado**: `.claude/plans/rustling-zooming-hearth.md`
- **Datos**: `data/Reto_data_20251023_122206.parquet`
- **Entrypoint**: `cli.py`
