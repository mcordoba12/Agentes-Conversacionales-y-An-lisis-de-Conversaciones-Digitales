# 🚀 IA RETO - Cloud Deployment Guide

**Despliegue 100% gratuito en cloud. Sin costos de infraestructura ni LLM.**

---

## 📋 Opciones de Acceso

### **Opción A: Dashboard (Recomendada para el profesor)**
```
URL: https://[tu-usuario]-ia-reto.streamlit.app
- Chat integrado
- Métricas en tiempo real
- Security events
- Cost tracking
- Fácil de usar desde browser
```

### **Opción B: API REST**
```
URL: https://ia-reto-agent.onrender.com/docs
- Documentación automática (Swagger)
- Endpoints: /chat, /metrics, /reset, /health
- JSON responses
```

### **Opción C: CLI Local (Desarrollo)**
```bash
python cli.py
```

---

## 🔧 Setup Detallado (Paso a Paso)

### **Paso 1: Obtener API Key Groq (GRATIS)**

1. Ir a: https://console.groq.com
2. Sign up (gratis)
3. Copiar API key (comienza con `gsk_`)
4. **Esta clave NO se acabará** - Groq ofrece free tier ilimitado

### **Paso 2: Preparar Repositorio**

```bash
# Asegurarse de que todo está en Git
git add -A
git commit -m "Add cloud deployment: app.py, render.yaml, Groq support"
git push origin main
```

**Archivos nuevos creados:**
- ✅ `app.py` - FastAPI web server
- ✅ `render.yaml` - Configuración para Render
- ✅ `DEPLOYMENT.md` - Este archivo

**Archivos modificados:**
- ✅ `agent/llm_factory.py` - Agregado soporte Groq (+30 líneas)
- ✅ `config.py` - Agregadas variables Groq (+3 líneas)
- ✅ `requirements.txt` - Agregado langchain-groq (+1 línea)
- ✅ `dashboard/app.py` - URL dinámicas + fixes (+2 líneas)

**Archivos SIN cambios:**
- ✅ `cli.py` - Sigue igual, funciona 100%
- ✅ `agent/graph.py` - Lógica del agente intacta
- ✅ `security/`, `observability/` - Todo funcional

---

## 🎯 Despliegue en la Nube (Gratuito)

### **Parte 1: Render - Backend (4 servicios)**

1. **Ir a:** https://render.com
2. **Sign up** (gratis)
3. **Conectar GitHub** a tu cuenta Render
4. **Crear 4 servicios** desde `render.yaml`:

   ```
   Opción A - Automático:
   - Render detecta render.yaml
   - 1 click = deploy de 4 servicios

   Opción B - Manual:
   - New Web Service
   - Conectar repo
   - Build: pip install -r requirements.txt
   - Start: python app.py
   ```

5. **Agregar Secret (importante):**
   - En Render dashboard → Settings → Environment
   - New Secret: `GROQ_API_KEY` = `gsk_...`

6. **Esperar despliegue:** ~5-10 minutos

   **URLs resultantes:**
   ```
   https://ia-reto-agent.onrender.com        (Main API)
   https://sentiment-mcp.onrender.com         (MCP 1)
   https://influence-mcp.onrender.com         (MCP 2)
   https://propagation-mcp.onrender.com       (MCP 3)
   ```

### **Parte 2: Streamlit Cloud - Dashboard**

1. **Ir a:** https://share.streamlit.io
2. **Sign in** con GitHub
3. **"New app"** → Seleccionar:
   ```
   Repository: tu-repo/IA-RETO
   Branch: main
   File: dashboard/app.py
   ```

4. **Configurar Secret (importante):**
   - En Streamlit dashboard
   - Secrets → `AGENT_SERVICE_URL` = `https://ia-reto-agent.onrender.com`

5. **Deploy automático:** ~2 minutos

   **URL resultante:**
   ```
   https://[tu-usuario]-ia-reto.streamlit.app
   ```

---

## ✅ Verificación: ¿Funciona Todo?

### **Test 1: Health Check**
```bash
curl https://ia-reto-agent.onrender.com/health
# Respuesta esperada:
# {"status":"ready","provider":"groq","timestamp":"2026-05-10T..."}
```

### **Test 2: Chat API**
```bash
curl -X POST https://ia-reto-agent.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"query":"¿Cuál es el sentimiento principal?"}'

# Respuesta esperada:
# {"response":"...", "tokens_used":342, "cost":0.0, "latency_ms":1200, ...}
```

### **Test 3: Dashboard**
```
Abrir en browser: https://[tu-usuario]-ia-reto.streamlit.app
- Debe mostrar: Chat input + Métricas
- Verificar conexión al agente (✅ verde)
- Hacer pregunta, debe responder en ~2-3s
```

---

## 💰 Costos Finales (Reales)

| Componente | Proveedor | Costo | Notas |
|-----------|-----------|-------|-------|
| **LLM** | Groq | $0 | Free tier ilimitado |
| **API Server** | Render | $0 | Free tier + cold starts (~20s) |
| **MCPs** | Render | $0 | Free tier x3 |
| **Dashboard** | Streamlit Cloud | $0 | Free tier ilimitado |
| **Database** | SQLite local | $0 | Incluido |
| **Total** | | **$0** | ✅ Completamente gratis |

---

## ⚡ Performance Notes

### **Latencia Esperada**

```
Local (CLI):
- Query: 0.5s (Groq ultra-rápido)
- Dashboard refresh: 10s

Cloud (Render + Streamlit):
- Query: 1-2s (+ cold start 20s si sleep)
- Dashboard refresh: 5-10s
```

### **Cold Starts en Render**

Render duerme servicios inactivos después de 15 minutos.
- Primera llamada después de inactividad: +20s
- Llamadas posteriores: normal

**Solución si el profesor quiere evitar:**
- Upgrade a plan pagado (no recomendado, es gratis con delay)
- O usar `curl` cada 10 min para mantener "caliente"

---

## 📊 URL para el Profesor

**Envíale SOLO ESTO:**

```
Dashboard: https://[tu-usuario]-ia-reto.streamlit.app

Acceso directo al chat + métricas
Abre en browser, no necesita terminal
```

---

## 🔄 Rollback Seguro

Si algo falla en cloud, rollback es muy fácil:

```bash
# Opción 1: Revertir deploy en Render
# Dashboard Render → Deployments → Select previous → Redeploy

# Opción 2: Volver a Git local
git revert <commit-hash>
git push

# Opción 3: El CLI local sigue funcionando
python cli.py
```

---

## 📝 Checklist Final

- [ ] API key Groq obtenida
- [ ] Repo pusheado a GitHub
- [ ] Render: 4 servicios desplegados
- [ ] Render: Secret GROQ_API_KEY configurado
- [ ] Streamlit Cloud: Dashboard desplegado
- [ ] Streamlit Cloud: Secret AGENT_SERVICE_URL configurado
- [ ] Test 1: `/health` retorna OK
- [ ] Test 2: `/chat` retorna respuesta
- [ ] Test 3: Dashboard conecta y responde
- [ ] Enviar URL al profesor: `https://[tu-usuario]-ia-reto.streamlit.app`

---

## 🆘 Troubleshooting

### **"Cannot connect to agent service"**
- Verificar que Render desplegó correctamente
- Esperar 5 minutos después de deploy
- Revisar logs en Render dashboard

### **"GROQ_API_KEY not configured"**
- Verificar que el secret está en Render
- Redeploy después de agregar secret
- Esperar 2 minutos

### **Dashboard lento**
- Normal en primera carga (cold start)
- Llamadas posteriores son más rápidas
- No es un error

### **Metrics no se actualizan**
- Hacer mínimo 3 preguntas para ver datos
- Refrescar browser manualmente
- Toggle "Auto-refresh" en dashboard

---

## 🎯 Lo Importante

✅ **CLI local sigue funcionando exactamente igual**
✅ **Todas las fases (1-6) están en producción**
✅ **Dashboard profesional en browser**
✅ **Costo: $0 completamente**
✅ **Profesor accede solo con URL**

---

**Listo para deploy. ¿Necesitas ayuda con algún paso?**
