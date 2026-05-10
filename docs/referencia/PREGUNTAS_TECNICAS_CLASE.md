# 🎓 Preguntas Técnicas — Clase IA RETO

---

## 🔒 SEGURIDAD (4 preguntas)

**1. ¿Cómo evadirías el regex que detecta "ignore"?**

Cambiando caracteres: "ign0re" no se detecta. O esperando 61 segundos para que se resetee el contador de intentos.

---

**2. ¿Por qué SQL injection es HIGH severity pero "override" es LOW?**

SQL injection ataca directamente la base de datos (peligro crítico). "Override" es un intento genérico menos específico. El sistema asigna severidad según el riesgo real de daño.

---

**3. ¿Cómo protegerías audit.db si alguien accede al servidor?**

Usar append-only (nunca DELETE, solo soft delete). O enviar logs en tiempo real a un servidor remoto certificado donde el atacante no puede borrar. O hash chaining (blockchain): cada fila contiene hash de la anterior, manipulaciones se detectan.

---

**4. ¿Qué información personal NO detecta el sistema?**

Nombres en contexto ("Juan García es CEO"), direcciones (formatos variados), información derivada (combinación de datos públicos = reidentificación), salud o sexualidad. Regex solo detecta patrones simples. Necesitarías NLP/ML para contexto.

---

## 🏗️ ARQUITECTURA (5 preguntas)

**5. ¿Qué decide si una pregunta usa Planning o no?**

El sistema detecta si la pregunta tiene múltiples partes: "Y", "además", múltiples puntos de pregunta. Si encuentra 2+ señales, activa Planning. Un LLM también puede evaluar: "¿cuántos pasos lógicos necesita esta pregunta?"

---

**6. ¿Qué diferencia hay entre STATE y MEMORY_BACKEND?**

STATE: memoria de 1 turno en RAM (rápida, se pierde al terminar). MEMORY_BACKEND: almacenamiento persistente en disco (lento, pero persiste). Si preguntaron sobre COVID hace 50 mensajes, ese dato estaba en STATE, pero se guardó en MEMORY. Ahora solo está en MEMORY hasta que lo necesites de nuevo.

---

**7. ¿Por qué los nodos son `async` si estamos en una sola conversación?**

Porque el servidor atiende múltiples usuarios simultáneamente. Si User 1 hace un HTTP request que tarda 2s, si fuera síncrono (bloqueante), User 2 esperaría 2s más. Con async, ambos requests se hacen en paralelo en corrutinas. 10 usuarios = 2s total, no 20s.

---

**8. Si el grafo termina en HITL_CHECK sin ejecutar la herramienta, ¿cómo el CLI lo sabe?**

El nodo setea `state["hitl_pending"] = True` antes de terminar. El CLI verifica `if agent.state.get("hitl_pending")` después de cada respuesta. Si es True, entra en loop de aprobación ("¿Aprobar? si/no") en lugar de pedir pregunta nueva.

---

**9. ¿Cuál es la diferencia entre INPUT, STATE y METADATA en AgentStateDict?**

INPUT: campos que nunca cambian (user_query, dataset). STATE: campos que se modifican entre nodos (messages, tool_results). METADATA: controlan el flujo (session_id, pattern_mode, hitl_pending). Cada nodo debe retornar el estado modificado o se pierden cambios.

---

## ⚡ PERFORMANCE (4 preguntas)

**10. ¿Por dónde fluyen los tokens desde OpenAI hasta el dashboard?**

OpenAI retorna tokens → se guardan en state → HTTP JSON al dashboard → se escriben en metrics.json → dashboard lee JSON cada 5s → renderiza en gráfico. Pérdida posible: si HTTP falla o disco lleno.

---

**11. Sabes ~1000ms es OpenAI, ~200ms es MCP. ¿Dónde están los otros 900ms?**

Podría ser: Ollama inference si está habilitado (500-2000ms), búsqueda en memoria (50-200ms), overhead del grafo (8 nodos × 50ms cada uno), retries por Reflection, o overhead de Streamlit rerun. Sin instrumentación distribuida (OpenTelemetry) es difícil saber exacto.

---

**12. El dashboard muestra "Quality Score = 0.9" pero el usuario dice "no me sirvió". ¿Por qué?**

Ragas mide relevancy (¿respondiste la pregunta?) y faithfulness (¿basado en datos?). Pero NO mide: correctness (¿es verdad?), completeness (¿falta info?), clarity (¿se entiende?), consistency (¿contradice respuestas anteriores?), factuality (¿hay alucinaciones?). Necesitas feedback del usuario como métrica final.

---

**13. ¿Qué pasa si un MCP está caído o muy lento?**

Si está caído: ConnectionError capturada, usuario ve error. Si es lento (>10s timeout): TimeoutError capturado, espera 10s luego error. Solución: Circuit Breaker (después de N fallos, rechaza inmediatamente), Retry Exponencial (reintentos con delay), Fallback a caché (retorna datos viejos si el fresco falla).

---

## 🎯 PATRONES (3 preguntas)

**14. ReAct muestra el razonamiento. Reflection se auto-evalúa. ¿Cuál es mejor para "¿cuál es el sentimiento?"**

ReAct: el usuario ve "Pensé en ejecutar analyze_sentiment, lo hice, obtuve POSITIVE 65%". Más tokens, más lento, pero mejor para debugging. Reflection: ejecuta en silencio, se auto-evalúa "¿es suficiente?" Si sí, termina rápido. Si no, reintenta. Mejor para performance. Para una pregunta simple, ReAct es mejor (transparencia + bajo costo de tokens).

---

**15. Planning detecta "Quiénes son los influencers Y el sentimiento de ellos" = 2 pasos. ¿Cómo?**

Busca señales: conectores ("y", "además"), múltiples temas. Si encuentra 2+, es complejo. O usa LLM: "¿cuántos pasos?" El LLM detecta dependencia (necesita influencers primero, luego analizar su sentimiento). Genera plan, lo ejecuta paso a paso.

---

**16. Para trading autónomo, chatbot atención, datos privados: ¿cuándo usas HITL?**

Trading: SÍ (irreversible, alto riesgo financiero, humano presente). Chatbot: NO (mata velocidad, usuario se frustra), solo si monto > $1000. Datos privados: SÍ (obligatorio por HIPAA/GDPR, privacidad > velocidad). Regla: HITL cuando acción es irreversible + sensible + hay alguien para aprobar.

---

## 💰 FINOPS (2 preguntas)

**17. La fórmula de costo es correcta, pero ¿qué no considera?**

Prompt caching (90% descuento en input cacheado). Batch processing (50% descuento). Fine-tuning (otro modelo, otro precio). Vision tokens (imágenes = más tokens). Volume tiers (si gastas mucho, descuento). Regional pricing (EU = +IVA). Error acumulado: 25-55% en 1000 queries.

---

**18. Sesión 1: $0.0004, Sesión 2: $0.0004, Sesión 3: $0.45. ¿Qué pasó?**

Probable: cambió de GPT-4o-mini a GPT-4 (precios 1000x más altos). O ejecutó 6000 queries por loop infinito. O procesó 400 imágenes sin saberlo. Detectar: Z-score (si está >3σ lejos del promedio = anomalía). Diagnosis: verificar modelo, input_tokens, num_requests. Alerta automática y bloqueo si supera threshold crítico.

---

## TOTAL: 18 preguntas técnicas retadoras
