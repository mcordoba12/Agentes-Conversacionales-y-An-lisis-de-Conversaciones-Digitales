"""
Interactive Streamlit Dashboard — Diferenciador
Visualiza en tiempo real: latencias, tokens, calidad, costos, eventos de seguridad
PLUS: Chat interface integrado (sin necesidad de terminal)
"""

import sys
import sqlite3
import time
from pathlib import Path
import requests
import json

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Resolver imports del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.metrics_store import read_metrics, clear_metrics

# Configuración del servicio
AGENT_SERVICE_URL = "http://localhost:8000"

# ============================================================================
# CONFIG
# ============================================================================

st.set_page_config(
    page_title="Agent Observability Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    .chat-message-user { background-color: #e8f4f8; padding: 10px; border-radius: 8px; margin: 5px 0; }
    .chat-message-agent { background-color: #f0f0f0; padding: 10px; border-radius: 8px; margin: 5px 0; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# INICIALIZAR SESSION STATE
# ============================================================================

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "agent_connected" not in st.session_state:
    st.session_state.agent_connected = False

# ============================================================================
# FUNCIONES DE CHAT
# ============================================================================

def check_agent_health():
    """Verificar si el servicio del agente está disponible"""
    try:
        resp = requests.get(f"{AGENT_SERVICE_URL}/", timeout=1)
        return resp.status_code == 200
    except:
        return False


def send_message_to_agent(question: str) -> dict:
    """Enviar mensaje al agente y obtener respuesta"""
    try:
        resp = requests.post(
            f"{AGENT_SERVICE_URL}/chat",
            json={"question": question},
            timeout=30
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"success": False, "error": f"Server error: {resp.status_code}"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout. Agent service may be slow."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "Cannot connect to agent service. Make sure agent_service.py is running on port 8000."}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# DATA LOADERS
# ============================================================================

@st.cache_data(ttl=5)
def load_metrics():
    """Cargar métricas del agente desde JSON"""
    records = read_metrics()
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


@st.cache_data(ttl=5)
def load_audit_events(limit=20):
    """Cargar eventos de seguridad desde SQLite audit.db"""
    db_path = Path(__file__).parent.parent / "data" / "audit.db"
    if not db_path.exists():
        return pd.DataFrame()

    try:
        conn = sqlite3.connect(str(db_path))
        query = """
            SELECT
                timestamp,
                session_id,
                SUBSTR(query, 1, 50) as query_preview,
                has_injection,
                injection_severity,
                pii_detected,
                tool_called
            FROM audit_log
            ORDER BY timestamp DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


# ============================================================================
# HEADER
# ============================================================================

st.title("🤖 Agent Observability Dashboard + Chat")
st.caption("💬 Chat Interface + Real-time Metrics Monitoring")

col_controls1, col_controls2 = st.columns(2)
with col_controls1:
    auto_refresh = st.toggle("Auto-refresh (10s)", value=True)
with col_controls2:
    if st.button("Refresh Now"):
        st.rerun()


# ============================================================================
# LOAD DATA
# ============================================================================

df = load_metrics()
audit_df = load_audit_events(limit=20)

# Verificar conexión con agente
st.session_state.agent_connected = check_agent_health()

# ============================================================================
# MAIN LAYOUT: CHAT (left) + METRICS (right)
# ============================================================================

chat_col, metrics_col = st.columns([1, 2.5])

# ============================================================================
# CHAT INTERFACE (LEFT COLUMN)
# ============================================================================

with chat_col:
    st.subheader("💬 Chat")

    # Status del agente
    if st.session_state.agent_connected:
        st.success("✓ Agent Service Connected", icon="✅")
    else:
        st.error("✗ Agent Service Offline", icon="❌")
        st.warning("""
        Make sure agent_service.py is running:
        ```bash
        python agent_service.py
        ```
        """)

    st.divider()

    # Pattern Mode Selector (Phase 6)
    st.markdown("#### 🎨 Pattern Mode")
    pattern = st.radio(
        "Select execution pattern:",
        options=["default", "react", "reflection", "planning", "hitl"],
        index=0,
        horizontal=False,
        help="Default: Standard execution\nReAct: Show Thought/Action/Reflection\nReflection: Self-evaluate responses\nPlanning: Decompose complex queries\nHITL: Require human approval before tool use"
    )

    # Cambiar patrón si está conectado
    if st.session_state.agent_connected and pattern != "default":
        try:
            resp = requests.post(f"{AGENT_SERVICE_URL}/mode/{pattern}", timeout=2)
            if resp.status_code == 200:
                st.success(f"✓ Pattern: {pattern}", icon="✅")
            else:
                st.warning(f"Could not set pattern: {resp.status_code}")
        except:
            st.warning("Could not change pattern")

    st.divider()

    # Mostrar historial de chat
    chat_container = st.container(height=400, border=True)
    with chat_container:
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                st.write(f"**You:** {msg['content']}")
            else:
                st.write(f"**Agent:** {msg['content']}")
                if msg.get("metadata"):
                    meta = msg["metadata"]
                    st.caption(f"⏱️ {meta.get('latency_ms', 0):.0f}ms | 💰 ${meta.get('cost', 0):.4f} | 🎯 {meta.get('quality', 0):.2f}")

    st.divider()

    # Input de chat
    if st.session_state.agent_connected:
        user_input = st.chat_input("Ask something...", disabled=False)

        if user_input:
            # Agregar mensaje del usuario al historial
            st.session_state.chat_messages.append({
                "role": "user",
                "content": user_input
            })

            # Enviar al agente
            with st.spinner("Thinking..."):
                response_data = send_message_to_agent(user_input)

            if response_data.get("success"):
                # Agregar respuesta del agente
                st.session_state.chat_messages.append({
                    "role": "agent",
                    "content": response_data.get("response", "No response"),
                    "metadata": {
                        "latency_ms": response_data.get("latency_ms", 0),
                        "cost": response_data.get("cost", 0),
                        "quality": response_data.get("quality", 0),
                        "tokens": response_data.get("tokens", {})
                    }
                })
                st.rerun()
            else:
                st.error(f"Error: {response_data.get('error', 'Unknown error')}")
    else:
        st.chat_input("Ask something...", disabled=True)
        st.info("Connect agent service to enable chat")

    # Controles
    st.divider()
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()
    with col_btn2:
        if st.button("Reset Agent", use_container_width=True):
            try:
                requests.post(f"{AGENT_SERVICE_URL}/reset", timeout=5)
                st.session_state.chat_messages = []
                st.rerun()
            except:
                st.warning("Could not reset agent")


# ============================================================================
# METRICS & ANALYTICS (RIGHT COLUMN)
# ============================================================================

with metrics_col:
    # ====================================================================
    # KPI ROW
    # ====================================================================

    st.subheader("Key Metrics")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        total_queries = len(df)
        st.metric(
            label="Total Queries",
            value=total_queries,
            delta=1 if len(df) > 1 else None
        )

    with kpi2:
        if not df.empty and "latency_ms" in df.columns:
            avg_latency = df["latency_ms"].mean()
            delta_latency = (
                df["latency_ms"].iloc[-1] - df["latency_ms"].iloc[-2]
                if len(df) > 1 else None
            )
            st.metric(
                label="Avg Latency",
                value=f"{avg_latency:.0f} ms",
                delta=f"{delta_latency:.0f} ms" if delta_latency else None
            )
        else:
            st.metric(label="Avg Latency", value="-- ms")

    with kpi3:
        if not df.empty and "session_cost_cumulative" in df.columns:
            session_cost = df["session_cost_cumulative"].iloc[-1]
            st.metric(
                label="Session Cost",
                value=f"${session_cost:.4f}"
            )
        else:
            st.metric(label="Session Cost", value="$0.0000")

    with kpi4:
        quality_score = 0.0
        if not df.empty:
            rel_scores = df["answer_relevancy"].dropna()
            faith_scores = df["faithfulness"].dropna()
            if len(rel_scores) > 0 and len(faith_scores) > 0:
                quality_score = (rel_scores.mean() + faith_scores.mean()) / 2

        st.metric(
            label="Quality Score",
            value=f"{quality_score:.2f}",
            delta="(avg of relevancy + faithfulness)" if quality_score > 0 else None
        )


    # ====================================================================
    # CHARTS ROW 1: Latency + Token Usage
    # ====================================================================

    st.subheader("Performance & Usage")

    row1_left, row1_right = st.columns(2)

    with row1_left:
        st.markdown("#### Response Latency (ms)")
        if not df.empty and "latency_ms" in df.columns:
            # Usar query_id como identificador
            chart_data = df[["query_id", "latency_ms"]].copy()
            chart_data["query_id"] = chart_data["query_id"].astype(str)

            fig = px.line(
                chart_data,
                x="query_id",
                y="latency_ms",
                markers=True,
                color_discrete_sequence=["#636EFA"],
                title="",
            )
            fig.update_layout(height=300, margin=dict(t=10, b=30, l=40, r=10))
            fig.update_xaxes(title="Query ID")
            fig.update_yaxes(title="Latency (ms)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No latency data yet. Start asking questions in the chat.")

    with row1_right:
        st.markdown("#### Token Usage per Query")
        if not df.empty and "input_tokens" in df.columns and "output_tokens" in df.columns:
            chart_data = df[["query_id", "input_tokens", "output_tokens"]].copy()
            chart_data["query_id"] = chart_data["query_id"].astype(str)

            fig = go.Figure(data=[
                go.Bar(name="Input Tokens", x=chart_data["query_id"], y=chart_data["input_tokens"]),
                go.Bar(name="Output Tokens", x=chart_data["query_id"], y=chart_data["output_tokens"]),
            ])
            fig.update_layout(
                barmode="stack",
                height=300,
                margin=dict(t=10, b=30, l=40, r=10),
                xaxis_title="Query ID",
                yaxis_title="Tokens",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No token data yet.")


    # ====================================================================
    # CHARTS ROW 2: Tool Distribution + Quality Scores
    # ====================================================================

    st.subheader("Insights")

    row2_left, row2_right = st.columns(2)

    with row2_left:
        st.markdown("#### Tool Distribution")
        if not df.empty and "tool_called" in df.columns:
            tool_counts = df["tool_called"].fillna("no_tool").value_counts().reset_index()
            tool_counts.columns = ["tool", "count"]

            fig = px.pie(
                tool_counts,
                names="tool",
                values="count",
                hole=0.3,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_layout(height=300, margin=dict(t=10, b=30, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No tool usage data yet.")

    with row2_right:
        st.markdown("#### Quality Scores (Ragas)")
        quality_data = df[["query_id", "answer_relevancy", "faithfulness"]].dropna()
        if not quality_data.empty:
            quality_data["query_id"] = quality_data["query_id"].astype(str)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=quality_data["query_id"],
                y=quality_data["answer_relevancy"],
                mode="lines+markers",
                name="Answer Relevancy",
                line=dict(color="#00CC96")
            ))
            fig.add_trace(go.Scatter(
                x=quality_data["query_id"],
                y=quality_data["faithfulness"],
                mode="lines+markers",
                name="Faithfulness",
                line=dict(color="#AB63FA")
            ))
            fig.update_layout(
                height=300,
                margin=dict(t=10, b=30, l=40, r=10),
                yaxis=dict(range=[0, 1]),
                xaxis_title="Query ID",
                yaxis_title="Score (0-1)",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ragas evaluation data not available. Enable OBS_RAGAS_ENABLED in config.")


    # ====================================================================
    # SECURITY EVENTS TABLE
    # ====================================================================

    st.subheader("Security Audit Log")

    if not audit_df.empty:
        # Función para colorear filas según severidad
        def highlight_security(row):
            if row.get("has_injection"):
                return ["background-color: #ffcccc"] * len(row)
            elif row.get("pii_detected"):
                return ["background-color: #ffffcc"] * len(row)
            return [""] * len(row)

        # Mostrar tabla con colores
        st.dataframe(
            audit_df.style.apply(highlight_security, axis=1),
            use_container_width=True,
            height=350
        )

        # Resumen de seguridad
        injection_count = audit_df[audit_df["has_injection"] == 1].shape[0]
        pii_count = audit_df[audit_df["pii_detected"] == 1].shape[0]

        col_sec1, col_sec2 = st.columns(2)
        with col_sec1:
            st.metric("Injection Attempts (last 20)", injection_count, delta="⚠️" if injection_count > 0 else "✓")
        with col_sec2:
            st.metric("PII Detections (last 20)", pii_count, delta="⚠️" if pii_count > 0 else "✓")

    else:
        st.info("No security events yet. Audit logging may be disabled.")


# ============================================================================
# AUTO-REFRESH
# ============================================================================

if auto_refresh:
    time.sleep(10)
    st.rerun()
