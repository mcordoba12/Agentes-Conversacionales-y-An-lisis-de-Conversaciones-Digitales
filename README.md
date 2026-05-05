# 🤖 Agente Conversacional - IA RETO ICESI

**Análisis Inteligente de Conversaciones Digitales**

---

## 📚 Estructura Organizad del Proyecto

```
IA-RETO/
├── agent/                  (Código del agente)
│   ├── graph.py            (Grafo LangGraph - 8 nodos, 4 conditional edges)
│   ├── state.py            (AgentStateDict con 20+ campos)
│   ├── tools.py            (3 tools nativos)
│   ├── prompts.py          (4 system prompts para patrones)
│   ├── llm_factory.py      (OpenAI/Ollama)
│   ├── cost_tracker.py     (FinOps)
│   ├── memory.py           (Gestión de memoria)
│   └── memory_backends/    (SQLite, ChromaDB, Hybrid)
│
├── services/               (3 Microservicios FastAPI)
│   ├── sentiment_mcp/      (Puerto 8001)
│   ├── influence_mcp/      (Puerto 8002)
│   └── propagation_mcp/    (Puerto 8003)
│
├── security/               (Enterprise Security)
│   ├── injection_detector.py   (30+ patrones)
│   ├── pii_detector.py         (Masking automático)
│   └── audit_logger.py         (ACID logging)
│
├── observability/          (Métricas y Evaluación)
│   ├── tracer.py           (Latency tracking)
│   └── ragas_evaluator.py  (Quality metrics)
│
├── dashboard/              (Streamlit)
│   ├── app.py              (4 KPIs + 4 gráficos + auditoría)
│   └── metrics_store.py
│
├── docs/                   📚 TODA LA DOCUMENTACIÓN AQUÍ
│   ├── presentacion/       (Diapositivas + guías)
│   │   ├── presentacion.html
│   │   ├── COMO_USAR_PRESENTACION.md
│   │   ├── PRESENTACION_INDICE.md
│   │   ├── PRESENTACION_RESUMEN.md
│   │   └── MEJORAS_REALIZADAS.md
│   │
│   ├── arquitectura/       (Diagramas y explicaciones)
│   │   ├── ARQUITECTURA_VISUAL.md
│   │   └── LANGGRAPH_VS_LANGCHAIN_EXPLICADO.md
│   │
│   ├── guias/              (Documentación técnica detallada)
│   │   ├── PROYECTO_EXPLICADO_SIMPLE.md
│   │   ├── TECHNICAL_REPORT.md
│   │   ├── ARCHITECTURE_DECISIONS.md
│   │   ├── POR_QUE_CADA_COSA.md
│   │   └── MCPs_TECHNICAL_GUIDE.md
│   │
│   ├── referencia/         (Glosario y demos)
│   │   ├── GLOSARIO_TERMINOS.md (738 líneas)
│   │   ├── PHASE_6_DEMO.md
│   │   └── DEMO_GUIDE.md
│   │
│   └── sesion/             (Resúmenes y mejoras)
│       └── SESSION_SUMMARY.md
│
├── config.py
├── cli.py
├── requirements.txt
└── README.md (ESTE ARCHIVO)
```

---

## 🎯 ¿POR DÓNDE EMPEZAR?

### Para Presentar al Profesor 🎬
```bash
# 1. Abre la presentación
docs/presentacion/presentacion.html
# Presiona: F (pantalla completa)

# 2. Lee los talking points
docs/presentacion/COMO_USAR_PRESENTACION.md

# 3. Referencia rápida si necesitas datos
docs/presentacion/PRESENTACION_INDICE.md
```

### Para Entender la Arquitectura 🏗️
```bash
# Explicación visual con diagramas
docs/arquitectura/ARQUITECTURA_VISUAL.md

# Comparación: LangGraph vs LangChain
docs/arquitectura/LANGGRAPH_VS_LANGCHAIN_EXPLICADO.md
```

### Para Responder Preguntas del Profesor 🤔
```bash
# Sin tecnicismos
docs/guias/PROYECTO_EXPLICADO_SIMPLE.md

# Análisis profundo
docs/guias/TECHNICAL_REPORT.md

# Por qué cada decisión
docs/guias/POR_QUE_CADA_COSA.md
docs/guias/MCPs_TECHNICAL_GUIDE.md
docs/guias/ARCHITECTURE_DECISIONS.md
```

### Referencias Rápidas 📖
```bash
# Diccionario de 738 líneas
docs/referencia/GLOSARIO_TERMINOS.md

# Cómo demostrar los 4 patrones
docs/referencia/PHASE_6_DEMO.md
```

---

## ⚡ QUICK START

### Terminal 1: Arrancar MCPs
```bash
python -m services.sentiment_mcp.main
python -m services.influence_mcp.main
python -m services.propagation_mcp.main
```

### Terminal 2: Arrancar CLI
```bash
python cli.py
```

### Terminal 3 (Opcional): Dashboard
```bash
streamlit run dashboard/app.py
```

### Ejemplo de uso:
```bash
You: ¿Quiénes son los más influyentes?
Agent: [Respuesta basada en datos]

You: mode react
You: ¿Cuál es el sentimiento?
Agent: [Muestra Thought → Action → Reflection]

You: mode hitl
Agent: [Pide confirmación antes de ejecutar]
```

---

## ✨ CARACTERÍSTICAS PRINCIPALES

### ✅ 6 Fases Completas
- Fase 1: LangGraph Agent + 3 Tools + MCPs
- Fase 2: FinOps (Cost Tracking)
- Fase 3: Long-term Memory
- Fase 4: Observability (Ragas)
- Fase 5: LLM Factory (OpenAI/Ollama)
- Fase 6: Design Patterns (ReAct, Reflection, Planning, HITL)

### 🏆 Diferenciador: Dashboard Profesional
- 4 KPIs en tiempo real
- 4 gráficos interactivos
- Tabla de auditoría con seguridad visible
- Cost tracking
- Quality metrics

### 🔒 Seguridad Enterprise
- Detección de inyecciones (30+ patrones)
- PII masking automático
- Auditoría ACID (SQLite)
- Rate limiting

### 🧠 Patrones Avanzados
- **ReAct:** Razonamiento explícito
- **Reflection:** Auto-evaluación
- **Planning:** Descomposición de queries
- **HITL:** Aprobación humana

---

## 🎓 NAVEGACIÓN POR TIPO DE NECESIDAD

| Necesidad | Archivo |
|-----------|---------|
| Presentar al profesor | `docs/presentacion/presentacion.html` |
| Qué decir en cada slide | `docs/presentacion/COMO_USAR_PRESENTACION.md` |
| Explicar arquitectura | `docs/arquitectura/ARQUITECTURA_VISUAL.md` |
| LangGraph vs LangChain? | `docs/arquitectura/LANGGRAPH_VS_LANGCHAIN_EXPLICADO.md` |
| Explicar sin tecnicismos | `docs/guias/PROYECTO_EXPLICADO_SIMPLE.md` |
| Análisis técnico profundo | `docs/guias/TECHNICAL_REPORT.md` |
| Por qué cada decisión | `docs/guias/POR_QUE_CADA_COSA.md` |
| Cómo funcionan los MCPs | `docs/guias/MCPs_TECHNICAL_GUIDE.md` |
| Diccionario de términos | `docs/referencia/GLOSARIO_TERMINOS.md` |
| Demo de los 4 patrones | `docs/referencia/PHASE_6_DEMO.md` |

---

## 📊 3 Herramientas Disponibles

```python
# Tool 1: Influencia
get_influence_metrics()
→ Retorna: JSON ranking de usuarios más influyentes

# Tool 2: Sentimiento
analyze_sentiment()
→ Retorna: POSITIVE/NEGATIVE/NEUTRAL percentage

# Tool 3: Propagación
trace_propagation(post_id)
→ Retorna: Árbol de retweets con BFS
```

---

## 💻 Tech Stack

```
Orquestación:     LangGraph (decisiones dinámicas)
API Web:          FastAPI (3 MCPs independientes)
Análisis datos:   Pandas (groupby, aggregation)
Búsqueda:         ChromaDB (semantic) + SQLite
LLM:              OpenAI (GPT-4o-mini) o Ollama (local, gratis)
Dashboard:        Streamlit (4 KPIs + 4 gráficos)
Seguridad:        Regex + Custom detectors
Evaluación:       Ragas (quality metrics)
```

---

## 🎬 PRESENTACIÓN

### Antes de Presentar
```
✅ Lee: docs/presentacion/COMO_USAR_PRESENTACION.md
✅ Abre: docs/presentacion/presentacion.html
✅ Practica una vez
```

### Durante la Presentación
```
1. Diapositivas 1-7: Intro (5 min)
2. Diapositivas 8-12: Patrones (10 min)
3. Diapositivas 13-16: Seguridad/Infraestructura (5 min)
4. Diapositiva 17: Demo en vivo (5 min)
5. Diapositiva 18-19: Diferenciador + Conclusión (1 min)
```

### Si el profesor pregunta
```
"¿LangGraph por qué?" → docs/arquitectura/LANGGRAPH_VS_LANGCHAIN_EXPLICADO.md
"¿MCPs cómo?" → docs/guias/MCPs_TECHNICAL_GUIDE.md
"¿Por qué FastAPI?" → docs/guias/POR_QUE_CADA_COSA.md
"¿Términos?" → docs/referencia/GLOSARIO_TERMINOS.md
```

---

## 📝 DOCUMENTACIÓN COMPLETADA

- ✅ Presentación interactiva (20 slides)
- ✅ Guía de arquitectura con diagramas
- ✅ Glosario de términos (738 líneas)
- ✅ Reportes técnicos
- ✅ Guías de uso y demo
- ✅ Justificación de decisiones

---

## ✅ ESTADO DEL PROYECTO

- ✅ Código completo (6 fases)
- ✅ Presentación profesional
- ✅ Documentación organizada
- ✅ Diferenciador claro (Dashboard)
- ✅ **LISTO PARA PRESENTAR**

---

**Para más detalles, navega por la carpeta `docs/` según tu necesidad.**

*Última actualización: 2026-05-04*
