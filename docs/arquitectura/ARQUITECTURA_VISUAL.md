# 🏗️ Arquitectura Visual Detallada

Explicación clara y visual de cómo funciona el sistema completo.

---

## ARQUITECTURA DE ALTO NIVEL

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                      👤 USUARIO FINAL                          │
│                   (CLI + Dashboard + API)                      │
│                                                                 │
└────────────────────────────┬──────────────────────────────────┘
                             │
                      📝 "¿Quién es influyente?"
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│            🧠 AGENTE CONVERSACIONAL (LangGraph)               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. Procesar Input                                        │  │
│  │    - Validar seguridad (inyecciones)                    │  │
│  │    - Detectar PII                                       │  │
│  │    - Recuperar contexto (memoria)                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 2. Decidir Patrón                                        │  │
│  │    - DEFAULT: ejecución normal                          │  │
│  │    - ReAct: mostrar razonamiento                        │  │
│  │    - Reflection: auto-evaluar                          │  │
│  │    - Planning: descomponer en pasos                    │  │
│  │    - HITL: pedir aprobación humana                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 3. Seleccionar Tool                                      │  │
│  │    - LLM decide automáticamente cuál tool usar          │  │
│  │    - Tool Calling Nativo (sin instrucciones manuales)  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                    (Si es necesario tool)                       │
│                             ▼                                   │
└─────────────────────┬──────────────────────────────────────────┘
                      │
                      │ HTTP Requests
                      │
         ┌────────────┼────────────┐
         │            │            │
         ▼            ▼            ▼
    ┌─────────┐  ┌─────────┐  ┌─────────┐
    │ Senti   │  │Influence│  │Propag   │
    │ MCP     │  │ MCP     │  │ MCP     │
    │ :8001  │  │ :8002  │  │ :8003  │
    └────┬────┘  └────┬────┘  └────┬────┘
         │            │            │
         │  Pandas    │  Pandas    │ BFS
         │  TextBlob  │  Groupby   │ Algorithm
         │            │            │
         └────────────┼────────────┘
                      │
              (Resultados de Tools)
                      │
                      ▼
         ┌─────────────────────────┐
         │  LLM genera respuesta    │
         │  basada en resultados   │
         └────────────┬────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │  Guardar en memoria     │
         │  (SQLite + ChromaDB)    │
         │  para contexto futuro   │
         └────────────┬────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │  Registrar en auditoría │
         │  (ACID guaranteed)      │
         │  - Query ejecutada      │
         │  - Inyección detectada  │
         │  - PII encontrada       │
         │  - Tool utilizado       │
         └────────────┬────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │  Calcular costos        │
         │  - Tokens usados        │
         │  - Cost por query       │
         │  - Cost acumulado       │
         └────────────┬────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │  Medir calidad (Ragas)  │
         │  - Answer Relevancy     │
         │  - Faithfulness         │
         └────────────┬────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │  Retornar al usuario    │
         │  + métricas             │
         └─────────────────────────┘
```

---

## COMPONENTES PRINCIPALES

### 1️⃣ AGENTE LangGraph (Orquestación Central)

**Ubicación:** `agent/graph.py`

**Responsabilidad:** Orquestar todo el flujo

**Características:**
- 8 nodos principales
- 4 conditional edges (decisiones dinámicas)
- StateGraph con 20+ campos de estado
- Integración de seguridad, memoria, costos, observabilidad

**Por qué LangGraph:**
- ✅ Decisiones dinámicas (LangChain NO tiene esto)
- ✅ Ciclos (para reintentarlo)
- ✅ Patrones avanzados (ReAct, Reflection, Planning, HITL)

---

### 2️⃣ 3 MICROSERVICIOS FastAPI

#### MCP 1: Sentiment Analysis (Puerto 8001)
```python
GET /analyze?text=...
→ {"POSITIVE": 45%, "NEGATIVE": 35%, "NEUTRAL": 20%, "UNKNOWN": 0%}
```
**Tech Stack:** FastAPI + TextBlob + Pandas
**Dataset:** 8,500 posts de redes sociales
**Algoritmo:** Simple pero efectivo

#### MCP 2: Influence Metrics (Puerto 8002)
```python
GET /get_influence
→ [{"author": "A", "score": 95}, {"author": "B", "score": 87}, ...]
```
**Tech Stack:** FastAPI + Pandas (groupby, aggregation)
**Métrica:** Basada en engagement, reach, retweets
**Escalabilidad:** O(n log n) con Pandas

#### MCP 3: Propagation Tracing (Puerto 8003)
```python
GET /trace?post_id=...
→ {
    "root": "user_A",
    "children": [
        {"user": "user_B", "children": [...]}
    ]
}
```
**Tech Stack:** FastAPI + BFS Algorithm
**Algoritmo:** Breadth-First Search (recorre por niveles)
**Complejidad:** O(V + E) para grafo de retweets

---

### 3️⃣ CAPAS DE DATOS Y SEGURIDAD

```
┌─────────────────────────────────────────┐
│      MEMORIA (Long-term Context)        │
├─────────────────────────────────────────┤
│  SQLite              ChromaDB            │
│  (Keywords)          (Semantic Search)   │
│  (Rápido)            (Preciso)           │
└─────────────────────────────────────────┘
           ▲                  ▲
           │                  │
┌──────────┴──────────────────┴──────────┐
│      CAPA DE SEGURIDAD                  │
├─────────────────────────────────────────┤
│  ┌────────────────────────────────────┐ │
│  │ Injection Detector                 │ │
│  │ - 30+ patrones regex              │ │
│  │ - Severidad: LOW/MEDIUM/HIGH      │ │
│  │ - Rate Limiter: 20 req/min        │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ PII Detector + Masking             │ │
│  │ - Email → [MASKED-EMAIL]          │ │
│  │ - Phone → [MASKED-PHONE]          │ │
│  │ - CC → [MASKED-CC]                │ │
│  │ - SSN, Passport → Auto-masked     │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │ Audit Logger (ACID)                │ │
│  │ - SQLite transacciones             │ │
│  │ - Registra cada query              │ │
│  │ - Trazabilidad completa            │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
           ▲
           │
┌──────────┴──────────────────────────────┐
│      CAPA DE OBSERVABILIDAD              │
├─────────────────────────────────────────┤
│  LocalTracer                Ragas        │
│  - Latency (ms)     Answer Relevancy     │
│  - Token Count      Faithfulness         │
│  - Success/Fail     Score (0.0 - 1.0)   │
└─────────────────────────────────────────┘
```

---

## FLUJO DE DATOS: PASO A PASO

### Ejemplo: "¿Quiénes son los usuarios más influyentes?"

```
PASO 1: Usuario Input
────────────────────
Input: "¿Quiénes son los usuarios más influyentes?"
│
├─ ✓ Validación seguridad (inyecciones)
├─ ✓ Detección PII
├─ ✓ Recuperar contexto (memoria anterior)
│
▼

PASO 2: LLM Procesamiento
────────────────────────
LLM piensa: "El usuario pregunta por influencia.
             Necesito llamar get_influence_metrics()"
│
├─ Decidir patrón (default/react/reflection/etc)
├─ Tool Calling: LLM decide usar get_influence_metrics
│
▼

PASO 3: Ejecutar Tool
────────────────────
HTTP GET → influence_mcp:8002
│
├─ FastAPI recibe request
├─ Pandas agrupa datos por autor
├─ Calcula influencia (engagement + reach + retweets)
├─ Retorna ranking JSON
│
▼

PASO 4: Generar Respuesta
─────────────────────────
LLM lee:
  "User A: score 95"
  "User B: score 87"
  "User C: score 72"

LLM genera respuesta natural:
  "Los usuarios más influyentes son..."
│
├─ Respuesta guardada en state
├─ Respuesta enviada al usuario
│
▼

PASO 5: Post-procesamiento
──────────────────────────
├─ Guardar turno en memoria (para contexto futuro)
├─ Registrar en auditoría (quién, qué, cuándo)
├─ Contar tokens usados
├─ Calcular costo ($0.0045)
├─ Evaluar calidad con Ragas
├─ Guardar métricas (latency, tokens, etc)
│
▼

PASO 6: Retornar Completo
─────────────────────────
Respuesta al usuario:
  "Los usuarios más influyentes son..."
  [Cost] Query: $0.0045 | Session: $0.0045 | Tokens: 285
  [Ragas] Relevancy: 0.92 | Faithfulness: 0.88
```

---

## VENTAJAS DE ESTA ARQUITECTURA

### 1. Modularidad
```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Senti    │     │Influence │     │Propag    │
│ MCP      │     │ MCP      │     │ MCP      │
└──────────┘     └──────────┘     └──────────┘
     ↑                ↑                 ↑
     └────────────────┼─────────────────┘
                  Intercambiables
                  Sin acoplamiento
```

**Beneficio:** Cada MCP puede escalarse, reemplazarse, o actualizarse independientemente

### 2. Escalabilidad
- **MCPs:** Corren en procesos separados (pueden estar en diferentes máquinas)
- **LLM:** Switcheable (OpenAI ↔ Ollama)
- **Memoria:** Intercambiable (SQLite ↔ ChromaDB ↔ Hybrid)
- **Seguridad:** Pluggable (agregar más detectores)

### 3. Fault Isolation
```
Si MCP Sentimiento falla:
  ├─ MCP Influencia sigue funcionando ✓
  ├─ MCP Propagación sigue funcionando ✓
  └─ Agente maneja error gracefully ✓

Si Ollama no está disponible:
  └─ Fallback a OpenAI automáticamente ✓
```

### 4. Transparencia
- **Logs ACID:** Quién preguntó, qué respondió, cuándo
- **Cost tracking:** Saber cuánto cuesta cada query
- **Ragas evaluation:** Medir calidad de respuestas
- **Dashboard:** Visualizar todo en tiempo real

---

## INTEGRACIONES CLAVE

### Seguridad
```
User Input
    ↓
[Injection Detector] ← 30+ patrones regex
    ↓
[PII Detector] ← Automático masking
    ↓
[Rate Limiter] ← 20 req/min por usuario
    ↓
[Audit Logger] ← ACID en SQLite
    ↓
Safe to Process ✓
```

### FinOps (Cost Awareness)
```
Query ejecutado
    ↓
[Token Counter]
  input: 150
  output: 45
    ↓
[Pricing] $0.15/1M (input), $0.60/1M (output)
    ↓
[Query Cost] = (150 * 0.15/1M) + (45 * 0.60/1M) = $0.0045
    ↓
[Session Cost] += Query Cost
    ↓
[Projections] Si gasto $0.0045/query → $2.25/mes
```

### Observabilidad (Ragas)
```
Query completo
    ↓
[Ragas Evaluator]
  Answer Relevancy: ¿Responde la pregunta?
  Faithfulness: ¿Está basado en datos reales?
    ↓
[Quality Score] 0.0 - 1.0
    ↓
[Dashboard] Visualiza tendencias
```

---

## DIFERENCIADOR: DASHBOARD

```
┌─────────────────────────────────────────────────────┐
│            📊 DASHBOARD STREAMLIT                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┬──────────────┐                   │
│  │  Total       │   Avg        │                   │
│  │  Queries: 12 │   Latency: 1.2s                 │
│  └──────────────┴──────────────┘                   │
│                                                     │
│  ┌──────────────┬──────────────┐                   │
│  │  Session     │   Quality    │                   │
│  │  Cost: $0.54 │   Score: 0.89                    │
│  └──────────────┴──────────────┘                   │
│                                                     │
│  ─────────────────────────────────────────────     │
│                                                     │
│  Latency Timeline       │  Token Usage Bar         │
│  ┌────────┐             │  ┌────┐                  │
│  │   ╱╲╱╲  │             │  │████│                 │
│  │  ╱  ╲  │             │  │███ │                 │
│  └────────┘             │  └────┘                  │
│                         │                          │
│  Tool Distribution      │  Quality Scores Line    │
│  [Influence] 40%        │  ┌──────┐               │
│  [Sentiment] 35%        │  │  ╱╲  │               │
│  [Propagation] 25%      │  │╱    ╲│               │
│                         │  └──────┘               │
│  ─────────────────────────────────────────────    │
│                                                     │
│  Audit Log Table                                  │
│  ┌─────────┬──────┬──────┬────────────────────┐   │
│  │ Query   │ Tool │ PII? │ Injection?         │   │
│  ├─────────┼──────┼──────┼────────────────────┤   │
│  │ ¿Quién? │ Inf. │  No  │ Safe               │   │
│  │ ¿Sent?  │ Sent │  Yes │ [MASKED-EMAIL]     │   │
│  │ ¿Prop?  │ Prop │  No  │ Safe               │   │
│  └─────────┴──────┴──────┴────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Lo que lo hace especial:**
- ✅ Tiempo real (actualiza cada query)
- ✅ Profesional (colores, gráficos, animaciones)
- ✅ Actionable (muestra dónde están los problemas)
- ✅ Security-first (tabla de auditoría visible)
- ✅ Cost-aware (muestra gastos)

---

## TECNOLOGÍAS USADAS

```
┌──────────────────────────────────────────┐
│         STACK TECNOLÓGICO                │
├──────────────────────────────────────────┤
│                                          │
│  Orquestación:                          │
│    LangGraph + LangChain + Pydantic     │
│                                          │
│  API Web:                               │
│    FastAPI + Uvicorn                    │
│                                          │
│  Datos:                                 │
│    Pandas + SQLite + ChromaDB           │
│                                          │
│  LLM:                                   │
│    OpenAI (GPT-4o-mini) o Ollama       │
│                                          │
│  Dashboard:                             │
│    Streamlit + Matplotlib               │
│                                          │
│  Seguridad:                             │
│    Regex patterns + Custom detectors    │
│                                          │
└──────────────────────────────────────────┘
```

---

## RESUMEN: POR QUÉ FUNCIONA

| Aspecto | Solución | Beneficio |
|---------|----------|-----------|
| **Orquestación** | LangGraph | Decisiones dinámicas + patrones |
| **Escalabilidad** | MCPs separados | Cada uno escala independientemente |
| **Seguridad** | Capas detectoras | Protección multi-nivel |
| **Confianza** | Ragas evaluation | Medimos calidad realmente |
| **Costos** | Token tracking | Sabemos exactamente cuánto gastamos |
| **Contexto** | Memory backends | Recordamos conversaciones anteriores |
| **Transparencia** | Audit logs | Trazabilidad completa |
| **Visibilidad** | Dashboard | Vemos todo en tiempo real |

---

## FLUJO FINAL: USUARIO A RESPUESTA

```
¿Quiénes son los influyentes?
           ↓
    [LangGraph]
      ↓  ↓  ↓
      ↓  ↓  ↓
 [MCPs] (paralelo)
      ↓  ↓  ↓
      ↓  ↓  ↓
 [Resultados]
      ↓
  [LLM respuesta]
      ↓
   [Seguridad]
      ↓
   [Memoria]
      ↓
  [Auditoría]
      ↓
  [Costos]
      ↓
  [Calidad]
      ↓
  [Dashboard]
      ↓
  Respuesta + Métricas
```

---

**Esta es la arquitectura que permite que tu agente sea profesional, seguro y confiable.** ✨
