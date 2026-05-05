# 📊 Cómo Usar las Diapositivas

## Opción 1: Presentación HTML Interactiva (Recomendado)

### Abrir en Navegador
```bash
# Doble clic en:
presentacion.html

# O:
# 1. Abre tu navegador (Chrome, Firefox, Edge)
# 2. Arrastra el archivo presentacion.html al navegador
# 3. Presiona F para pantalla completa
```

### Controles de Navegación
- **Flechas →/←** — Siguiente/Anterior diapositiva
- **Espacio** — Siguiente diapositiva
- **ESC** — Salir de pantalla completa
- **S** — Mostrar notas del orador (si las hay)
- **F** — Pantalla completa
- **B** — Fondo negro (pausa)

### Ventajas del HTML
✓ No requiere software adicional
✓ Funciona en cualquier navegador
✓ Animaciones suaves
✓ Tema profesional oscuro
✓ Fácil de compartir

---

## Opción 2: PowerPoint (.pptx)

### Usar en PowerPoint/Keynote/LibreOffice
```
1. Busca: presentacion_diapositivas.pptx
2. Abre con Microsoft PowerPoint, Google Slides, o LibreOffice
3. Edita libremente si lo necesitas
```

### Ventajas del PowerPoint
✓ Editable completamente
✓ Agregar notas del orador
✓ Cambiar temas/colores
✓ Insertar videos/gifs
✓ Compatible con presentadores remotos (Zoom, Teams)

---

## Estructura de las Diapositivas

| Nro | Tema | Duración |
|-----|------|----------|
| 1 | Portada | 30 seg |
| 2 | Índice | 1 min |
| 3 | El Problema | 1 min |
| 4 | Arquitectura | 1.5 min |
| 5 | LangGraph vs LangChain | 1.5 min |
| 6 | 3 Tools Nativos | 1.5 min |
| 7 | Tool Calling | 1 min |
| 8-12 | Patrones (5 diapositivas) | 7.5 min |
| 13 | Seguridad | 1.5 min |
| 14 | FinOps | 1 min |
| 15 | Observabilidad | 1 min |
| 16 | Dashboard | 1 min |
| 17 | Demo en Vivo | 2 min |
| 18 | Conclusión | 1 min |

**Total: ~25 minutos (sin incluir demo interactiva)**

---

## Puntos Clave a Mencionar en Cada Diapositiva

### Diapositiva 1: Portada
- Presentarse: "Soy [Nombre], octavo semestre"
- Contextualizar: "Este es el Reto ICESI, un agente conversacional para analizar conversaciones digitales"

### Diapositiva 2: Índice
- Recorrer brevemente cada tema
- "Cubriremos arquitectura, herramientas, patrones avanzados y seguridad"

### Diapositiva 3: Problema
- "¿Cómo analizar 8,500 posts de forma inteligente?"
- "¿Cómo asegurar que las respuestas son confiables?"
- Enfatizar: sentimiento, influencia, propagación

### Diapositiva 4: Arquitectura
- "Tenemos un agente central (LangGraph) que orquesta 3 microservicios"
- Cada microservicio es independiente y escalable

### Diapositiva 5: LangGraph vs LangChain
- "LangChain es para cadenas lineales"
- "LangGraph permite decisiones dinámicas = CRÍTICO para nuestros patrones"
- Tabla muestra que LangGraph hace TODO lo que necesitamos

### Diapositiva 6-7: Tools & Tool Calling
- "3 herramientas que el LLM puede usar automáticamente"
- Tool calling nativo = LLM decide cuándo usarlas
- No necesita instrucciones manuales (Pydantic + decoradores)

### Diapositivas 8-12: Patrones
- DEFAULT: "Rápido, sin explicación"
- ReAct: "Vemos el razonamiento paso a paso"
- Reflection: "Auto-evalúa, reintenta si es necesario"
- Planning: "Para preguntas complejas"
- HITL: "Control humano antes de ejecutar acciones críticas"

### Diapositiva 13: Seguridad
- Mencionar: "30+ patrones de inyección"
- "Detección automática de datos personales"
- "Cada query se registra (auditoría ACID)"

### Diapositiva 14: FinOps
- "Rastreamos cada token que usamos"
- "Proyectamos costos mensuales/anuales"
- "Opción de usar Ollama (gratis, local)"

### Diapositiva 15: Observabilidad
- "Ragas mide calidad de respuestas"
- "Relevancia + Faithfulness = confianza en el sistema"

### Diapositiva 16: Dashboard
- "Visualización en tiempo real"
- "KPIs + gráficos + auditoría"

### Diapositiva 17: Demo
- Ejecutar los comandos paso a paso
- Mostrar respuestas normales
- Luego cambiar a `mode react` para mostrar razonamiento
- Cambiar a `mode hitl` para mostrar aprobación humana

### Diapositiva 18: Conclusión
- Recapitular los 6 logros principales
- Enfatizar que todo está implementado y documentado

---

## Tips para la Presentación

### Antes de Presentar
1. ✓ Abre la presentación HTML en pantalla completa
2. ✓ Verifica que los MCPs y CLI están listos
3. ✓ Haz un "dry run" (ensayo) de la demo en vivo
4. ✓ Abre el dashboard en otra pestaña (para mostrar al final)

### Durante la Presentación
1. **Mantén el ritmo:** ~25 minutos de slides + 5 min de demo = 30 min total
2. **Interacción:** Haz preguntas como "¿Alguien sabe qué es LangGraph?"
3. **Demo:** Muestra REALMENTE cómo funciona (no solo hablar)
4. **Confianza:** Tienes 6 fases implementadas — muéstratela al profesor

### Puntos Que el Profesor Probablemente Pregunte
- "¿Por qué LangGraph y no otra solución?"
  → "Porque necesitamos decisiones dinámicas, ciclos, y patrones como ReAct"

- "¿Cómo garantizas seguridad?"
  → "Detección de inyecciones + PII masking + auditoría ACID"

- "¿Cuál es el costo real?"
  → "Con GPT-4o-mini cuesta X centavos por query. Ollama es gratis local."

- "¿Qué es tool calling?"
  → "El LLM decide automáticamente qué herramientas necesita. Mira aquí..."

---

## Archivos de Referencia (Para Mencionarlos)

Puedes decir: "Si quieres más detalles, tengo documentación completa:"

- **GLOSARIO_TERMINOS.md** — 738 líneas explicando cada concepto
- **TECHNICAL_REPORT.md** — Análisis profundo de la arquitectura
- **POR_QUE_CADA_COSA.md** — Por qué elegí cada tecnología
- **PHASE_6_DEMO.md** — Guía completa de los 4 patrones

---

## Checklist Antes de Presentar

```
[ ] Presentación HTML abierta en navegador
[ ] Navegador en pantalla completa (F)
[ ] MCPs corriendo en terminales separadas
[ ] CLI listo para usar (python cli.py)
[ ] Dataset cargado (8,500 posts)
[ ] Dashboard Streamlit abierto (opcional, para mostrar al final)
[ ] Conexión a internet estable (para OpenAI API)
[ ] O Ollama corriendo (si no tienes internet)
[ ] Micrófono y speaker funcionando
[ ] Notas/apuntes a mano (por si necesitas consultar)
```

---

## ¿Problemas con la Presentación?

**P: El HTML no se abre**
- R: Intenta arrastrarlo al navegador, o abre: `file:///ruta/presentacion.html`

**P: Las animaciones van lenta**
- R: Usa un navegador moderno (Chrome, Edge). Evita Firefox si tienes muchas tabs.

**P: Quiero editar las diapositivas**
- R: Usa el PowerPoint (`.pptx`) en lugar del HTML

**P: ¿Puedo hacer presentación remota (Zoom)?**
- R: Sí, comparte la pantalla del navegador. Funciona perfecto.

---

## ¡Éxito en tu Presentación! 🎓

Tienes:
- ✓ Arquitectura moderna (LangGraph + MCPs)
- ✓ 3 herramientas funcionales
- ✓ 4 patrones avanzados
- ✓ Seguridad enterprise
- ✓ Dashboard profesional
- ✓ 6 fases completas

Muéstrate confiado. El trabajo es sólido. 💪
