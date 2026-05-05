# Phase 6 Demo: Design Patterns (ReAct, Reflection, Planning, HITL)

**Complete guide to demonstrating all 4 advanced design patterns**

---

## QUICK START

```bash
# Terminal 1: Start the MCPs
python -m services.sentiment_mcp.main
python -m services.influence_mcp.main
python -m services.propagation_mcp.main

# Terminal 2: Start the CLI agent
python cli.py
```

When you see "Escribe tu pregunta", Phase 6 is ready to test.

---

## PATTERN 1: DEFAULT MODE (Normal execution, no explanation)

**Purpose:** Baseline behavior — agent executes tools without showing reasoning

**Demo:**
```
You: mode default
Agent: [Pattern] Modo normal activado

You: ¿Quiénes son los usuarios más influyentes?
Agent: Los usuarios más influyentes son...
[Cost] Query: $0.0045 | Session: $0.0045 | Tokens: 285
```

**What happens:**
- User asks question → Agent thinks "need tool?" → YES → Execute tool → Generate response
- No reasoning shown, just the answer
- Fastest mode (no extra LLM calls for reflection)

---

## PATTERN 2: ReAct PATTERN (Explicit reasoning)

**Purpose:** Show the agent's thought process, action, and reflection

**Demo:**
```
You: mode react
Agent: [Pattern] Patrón 'react' activado

You: ¿Quiénes son los usuarios más influyentes?
[Procesando...]
Agent:
Thought: El usuario pregunta sobre influencia. Necesito ejecutar get_influence_metrics.

Action: Ejecutar get_influence_metrics()

Observation: Los datos muestran que:
- Usuario A: score 95
- Usuario B: score 87
- Usuario C: score 72

Reflection: La respuesta es clara. Puedo now generar una respuesta final.

Respuesta Final: Los usuarios más influyentes son A, B y C con scores 95, 87 y 72 respectivamente.
```

**What happens:**
1. Agent thinks: "Necesito get_influence_metrics"
2. Agent acts: calls the tool
3. Agent observes: sees the results
4. Agent reflects: decides the answer is good
5. Agent responds: generates natural language response

**Code location:** `agent/prompts.py:get_react_system_prompt()`

---

## PATTERN 3: REFLECTION PATTERN (Auto-evaluation)

**Purpose:** Agent evaluates if its answer is sufficient; retries if not

**Demo:**
```
You: mode reflection
Agent: [Pattern] Patrón 'reflection' activado

You: ¿Cuál es el sentimiento general y quiénes son los más influyentes?
[Procesando...]
Agent:

[Reflection] Evaluando respuesta...
- Pregunta 1: "¿Cuál es el sentimiento?" → tool resultado
- Pregunta 2: "¿Quiénes son los influyentes?" → tool resultado

[Reflection] Evaluación: AMBIGUOUS (pregunta tiene 2 partes)
[Reflection] Acción: Reintentando con enfoque más estructurado...

[Segundo intento]
Sentimiento: 45% positivo, 35% negativo, 20% neutral
Influencia: Top 3 usuarios son A, B, C

[Reflection] Evaluación: SUFFICIENT ✓

Respuesta Final: El sentimiento general es mixto (45% positivo), y los usuarios más influyentes son A, B y C.
```

**What happens:**
1. Agent executes tool 1 → gets sentiment
2. Agent executes tool 2 → gets influence
3. Agent evaluates: "¿Es suficiente?"
4. If NO → reintenta (máximo 1 retry)
5. If YES → genera respuesta final

**Code location:** `agent/prompts.py:get_reflection_system_prompt()`

---

## PATTERN 4: PLANNING PATTERN (Multi-step decomposition)

**Purpose:** Break complex queries into steps before executing

**Demo:**
```
You: mode planning
Agent: [Pattern] Patrón 'planning' activado

You: ¿Quiénes son los usuarios más influyentes y cuál es el sentimiento general?
[Procesando...]
Agent:

[Planning] Descomponiendo pregunta...

PLAN GENERADO:
Paso 1: Obtener influencia de usuarios
  - Tool: get_influence_metrics()
  - Objetivo: Identificar top 3 usuarios

Paso 2: Obtener sentimiento general
  - Tool: analyze_sentiment()
  - Objetivo: Distribución emocional

Paso 3: Combinar resultados
  - Correlacionar influencia con sentimiento
  - Generar análisis final

[Ejecutando plan...]

[Paso 1] ✓ Completado
  Resultado: A (95), B (87), C (72)

[Paso 2] ✓ Completado
  Resultado: POSITIVE 45%, NEGATIVE 35%, NEUTRAL 20%

[Paso 3] ✓ Completado
  Análisis: Los influencers principales generan sentimiento mixto

RESPUESTA FINAL:
Los usuarios más influyentes son:
1. Usuario A (score 95) - Genera sentimiento mixto
2. Usuario B (score 87) - Receptivo a feedback
3. Usuario C (score 72) - Moderador neutral

Sentimiento General: 45% positivo, 35% negativo, 20% neutral
```

**What happens:**
1. Agent generates JSON plan with steps
2. Agent executes step 1 → saves result
3. Agent executes step 2 → saves result
4. Agent evaluates step 3 → decide if need more steps
5. Agent generates final response combining all steps

**Code location:** `agent/prompts.py:get_planning_system_prompt()`

---

## PATTERN 5: HITL PATTERN (Human approval required)

**Purpose:** Pause before executing tools, ask for user confirmation

**Demo:**
```
You: mode hitl
Agent: [Pattern] Patrón 'hitl' activado

You: ¿Quiénes son los usuarios más influyentes?
[Procesando...]

[HITL CONFIRMATION REQUIRED]
Tool: get_influence_metrics
Input: {}

Execute tool? (si/no): si
[HITL] Aprobado. Ejecutando tool...

Agent: Los usuarios más influyentes son...

---

SEGUNDO EJEMPLO (USER CANCELA):

You: ¿Cómo se propagó el post ABC123?
[Procesando...]

[HITL CONFIRMATION REQUIRED]
Tool: trace_propagation
Input: {'post_id': 'ABC123'}

Execute tool? (si/no): no
[HITL] Action cancelled.
Agent: Acción cancelada. Si deseas que ejecute este análisis, responde 'si' en la próxima pregunta.
```

**What happens:**
1. Agent routes to tool execution
2. Instead of executing → agent writes approval message
3. CLI detects `hitl_pending` flag
4. CLI shows tool info and asks for confirmation
5. If YES → CLI manually calls execute_tool() + generate_response()
6. If NO → CLI cancels and returns to user

**Code location:**
- Graph: `agent/graph.py:node_hitl_check()`
- CLI: `cli.py:lines 266-318`

---

## COMPARISON TABLE: WHICH PATTERN FOR WHICH USE CASE?

| Use Case | Pattern | Why? |
|----------|---------|------|
| Quick answers | **default** | Fast, no overhead |
| Debugging reasoning | **react** | See thought process |
| Complex questions | **reflection** | Self-correct if wrong |
| Multi-step queries | **planning** | Organize work |
| Sensitive actions | **hitl** | Human controls execution |
| Learning what agent does | **react** | Educational, explicit |
| Production speed | **default** | Minimal latency |
| Quality assurance | **reflection** | Validate answers |

---

## TESTING CHECKLIST

- [ ] **Default Mode**
  - [ ] Agent responds without showing reasoning
  - [ ] Response is natural, direct
  - [ ] Cost is minimal (1 LLM call)

- [ ] **ReAct Mode**
  - [ ] Shows "Thought: ..."
  - [ ] Shows "Action: ..."
  - [ ] Shows "Reflection: ..."
  - [ ] Cost is higher (2 LLM calls for trace)

- [ ] **Reflection Mode**
  - [ ] Shows "[Reflection] Evaluando..."
  - [ ] If INSUFFICIENT → shows "[Reflection] Reintentando..."
  - [ ] Max 1 retry happens
  - [ ] Shows "SUFFICIENT ✓" when done

- [ ] **Planning Mode**
  - [ ] Shows plan with numbered steps
  - [ ] Executes steps in order
  - [ ] Shows "✓ Completado" for each step
  - [ ] Combines results in final answer

- [ ] **HITL Mode**
  - [ ] Shows tool name before execution
  - [ ] Waits for user input (si/no)
  - [ ] If si → executes and responds
  - [ ] If no → cancels action
  - [ ] Handles typos gracefully

---

## TECHNICAL VERIFICATION

### Check that Phase 6 is fully implemented:

```bash
# Verify all 4 nodes exist
grep -n "def node_react_think\|def node_reflect\|def node_plan\|def node_hitl_check" agent/graph.py

# Verify conditional edges are connected
grep -n "add_conditional_edges" agent/graph.py

# Verify state fields exist
grep -n "hitl_pending\|reflection_insufficient\|plan_steps\|react_trace" agent/state.py

# Verify prompts are complete
grep -n "def get_react_system_prompt\|def get_reflection_system_prompt\|def get_planning_system_prompt\|def get_hitl_approval_prompt" agent/prompts.py

# Verify CLI mode command
grep -n "startswith(\"mode\")" cli.py

# Verify HITL CLI handling
grep -n "hitl_pending" cli.py
```

All should return results.

---

## ADVANCED: COMBINING PATTERNS

You can use different patterns for different turnas:

```
You: mode default
You: ¿Quiénes son los influyentes?
Agent: (responde sin reasoning)

You: mode react
You: ¿Cuál es el sentimiento?
Agent: (muestra Thought/Action/Reflection)

You: mode reflection
You: ¿Son consistentes los datos?
Agent: (auto-evalúa)

You: mode planning
You: Quiero análisis completo de influencia y sentimiento
Agent: (genera plan de 2 pasos)
```

---

## FOR THE PROFESSOR: KEY POINTS TO HIGHLIGHT

1. **Flexibility**: Mismo agente, 5 modos diferentes — demuestra arquitectura modular
2. **Conditional Edges**: ReAct → execute_tool es diferente que default → execute_tool
3. **State Management**: pattern_mode en estado controla todo el flujo
4. **Human Control**: HITL muestra que es posible pedir aprobación (importante para IA segura)
5. **Self-Reflection**: Reflection pattern que reintenta si no es suficiente
6. **Cost Awareness**: Mostrar que cada patrón tiene costo diferente (tokens)

---

## TROUBLESHOOTING

**Q: ReAct mode shows normal response, not reasoning**
- A: Check `agent/prompts.py:get_react_system_prompt()` format
- A: Verify `node_react_think()` parses response correctly

**Q: HITL doesn't ask for confirmation**
- A: Check `agent/state.get("pattern_mode")` is "hitl"
- A: Check `agent.state.get("hitl_pending")` is True after chat()
- A: Check CLI line 280: `if agent.state.get("hitl_pending"):`

**Q: Reflection keeps retrying forever**
- A: Check `reflection_retries` counter in code (max should be 1)
- A: Verify `route_after_reflect()` function logic

**Q: Planning doesn't generate steps**
- A: Check if query is "complex" enough (has " y " or multiple ?)
- A: Check `route_after_input()` is routing to "node_plan"

---

## FILES MODIFIED IN PHASE 6

- `agent/graph.py` — 4 new nodes + 4 conditional edges
- `agent/state.py` — Phase 6 fields added
- `agent/prompts.py` — 4 system prompts (already existed)
- `cli.py` — HITL handling + mode command + help messages
- `config.py` — pattern_mode configuration

No new dependencies added.

---

## NEXT: Integration with Professor's Requirements

This Phase 6 demonstrates:
- ✓ Advanced AI patterns (ReAct, Reflection, Planning)
- ✓ Human control (HITL)
- ✓ Flexible agent architecture
- ✓ Cost awareness per pattern
- ✓ Conditional routing (LangGraph strength)

Perfect for explaining why LangGraph was chosen over LangChain!
