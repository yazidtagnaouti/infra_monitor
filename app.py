import sys, os

sys.path.insert(0, os.path.dirname(__file__))

try:
    from config import GROQ_API_KEY as _LOCAL_GROQ_KEY

    if str(_LOCAL_GROQ_KEY or "").strip():
        os.environ.setdefault("GROQ_API_KEY", str(_LOCAL_GROQ_KEY).strip())
except ImportError:
    pass

import json
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from pipeline import build_pipeline

st.set_page_config(page_title="Infrastructure Monitor", page_icon="🖥️", layout="wide")

# Inject Streamlit Cloud secrets into env
try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🖥️ Infra Monitor")
    uploaded = st.file_uploader("Fichier JSON", type=["json"])

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
        if api_key:
            os.environ["GROQ_API_KEY"] = api_key
    else:
        st.success("✅ Clé API détectée")

    run = st.button("▶ Lancer le pipeline", type="primary", width="stretch")

    with st.expander("Déploiement Streamlit Cloud"):
        st.caption("En local : remplissez `config.py` (gitignoré) ou copiez `config.example.py`.")
        st.code("GROQ_API_KEY = 'gsk_...'", language="toml")
        st.caption("Cloud : Settings → Secrets → coller ci-dessus")


@st.cache_data(show_spinner=False)
def run_pipeline(data_str, _key):
    records = json.loads(data_str)
    return build_pipeline().invoke({"records": records})


# ── Chargement des données ────────────────────────────────────────────────────
if uploaded:
    raw = json.load(uploaded)
elif os.path.exists(os.path.join(os.path.dirname(__file__), "data.json")):
    with open(os.path.join(os.path.dirname(__file__), "data.json")) as f:
        raw = json.load(f)
else:
    raw = None

# ── Lancement ─────────────────────────────────────────────────────────────────
if run:
    if not raw:
        st.error("Aucune donnée disponible.")
        st.stop()
    with st.spinner("Pipeline en cours…"):
        result = run_pipeline(json.dumps(raw), os.getenv("GROQ_API_KEY", ""))
    st.session_state["report"] = result["report"]
    st.session_state["records"] = raw

# ── Dashboard ─────────────────────────────────────────────────────────────────
if "report" not in st.session_state:
    st.info("⬆️ Chargez un fichier JSON puis cliquez **Lancer le pipeline**.")
    st.stop()

report  = st.session_state["report"]
records = st.session_state["records"]
metrics = report["metrics"]
services = report["services"]
anom    = report["anomalies"]
recos   = report["recommendations"]
df      = pd.DataFrame(records)
df["timestamp"] = pd.to_datetime(df["timestamp"])

st.title("Infrastructure Monitor")

# ── KPIs ──────────────────────────────────────────────────────────────────────
score = report["health_score"]
score_color = "#28a745" if score >= 80 else "#fd7e14" if score >= 60 else "#dc3545"

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Health Score", f"{score}/100")
k2.metric("CPU p95",      f"{metrics['cpu_usage']['p95']}%",   delta=f"max {metrics['cpu_usage']['max']}%",   delta_color="inverse")
k3.metric("RAM p95",      f"{metrics['memory_usage']['p95']}%", delta=f"max {metrics['memory_usage']['max']}%", delta_color="inverse")
k4.metric("Latence p95",  f"{metrics['latency_ms']['p95']}ms", delta=f"max {metrics['latency_ms']['max']}ms",  delta_color="inverse")
k5.metric("Anomalies",    anom["total"],                        delta=f"{anom['critical']} critiques",          delta_color="inverse")

st.divider()

# ── Onglets ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Métriques", "🚨 Anomalies", "💡 Recommandations", "🔧 Services", "📄 JSON"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        fig = px.line(df, x="timestamp", y=["cpu_usage", "memory_usage"], title="CPU & RAM (%)")
        fig.add_hline(y=85, line_dash="dash", line_color="red", annotation_text="Seuil 85%")
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig2 = px.line(df, x="timestamp", y="latency_ms", title="Latence (ms)")
        fig2.add_hline(y=300, line_dash="dash", line_color="red", annotation_text="Seuil 300ms")
        st.plotly_chart(fig2, width="stretch")
    c3, c4 = st.columns(2)
    with c3:
        fig3 = px.line(df, x="timestamp", y=["disk_usage", "temperature_celsius"], title="Disque (%) & Température (°C)")
        st.plotly_chart(fig3, width="stretch")
    with c4:
        fig4 = px.line(df, x="timestamp", y="error_rate", title="Taux d'erreur")
        fig4.add_hline(y=0.08, line_dash="dash", line_color="red", annotation_text="Seuil 0.08")
        st.plotly_chart(fig4, width="stretch")

    rows = [{"Métrique": m, **s} for m, s in metrics.items()]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        bm = anom["by_metric"]
        fig_b = px.bar(x=list(bm.values()), y=list(bm.keys()), orientation="h", title="Anomalies par métrique")
        st.plotly_chart(fig_b, width="stretch")
    with c2:
        fig_p = go.Figure(go.Pie(
            labels=["Critiques", "Warnings"],
            values=[anom["critical"], anom["warning"]],
            marker_colors=["#dc3545", "#fd7e14"], hole=0.5,
        ))
        fig_p.update_layout(title="Sévérité", height=300)
        st.plotly_chart(fig_p, width="stretch")

    anom_full = [a for a in report.get("anomalies_list", []) if a]
    adf = pd.DataFrame([
        {"ts": r["timestamp"], "metric": m, "value": v, "severity": s}
        for r in records
        for m, levels in {"cpu_usage": (70,85), "memory_usage": (75,85),
                          "latency_ms": (200,300), "disk_usage": (75,85)}.items()
        if (v := r.get(m)) and v >= (s := "critical" if v >= levels[1] else "warning" if v >= levels[0] else None, levels[0])[1] and s
    ] if False else [])

    sev_filter = st.multiselect("Sévérité", ["critical", "warning"], default=["critical", "warning"])
    all_anomalies = []
    for r in records:
        from nodes.anomaly import THRESHOLDS
        for metric, levels in THRESHOLDS.items():
            val = r.get(metric)
            if not val: continue
            if val >= levels["crit"]:
                all_anomalies.append({"Timestamp": r["timestamp"], "Métrique": metric, "Valeur": val, "Sévérité": "critical"})
            elif val >= levels["warn"]:
                all_anomalies.append({"Timestamp": r["timestamp"], "Métrique": metric, "Valeur": val, "Sévérité": "warning"})

    filtered = [a for a in all_anomalies if a["Sévérité"] in sev_filter]
    st.dataframe(pd.DataFrame(filtered), width="stretch", height=300, hide_index=True)

with tab3:
    llm = bool(os.getenv("GROQ_API_KEY"))
    st.caption(
        "✅ Recommandations via Groq (LLM)"
        if llm
        else "ℹ️ Règles Python — ajoutez une clé Groq (config.py ou sidebar) pour l'enrichissement IA"
    )
    for r in recos:
        icon = "🔴" if r.get("priority") == "Critique" else "🟠" if r.get("priority") == "Haute" else "🔵"
        with st.expander(f"{icon} [{r.get('id')}] {r.get('title')}", expanded=(r.get("priority") == "Critique")):
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Priorité** : {r.get('priority')}")
            c2.markdown(f"**Effort** : {r.get('effort')}")
            c3.markdown(f"**Impact** : {r.get('impact')}")
            st.markdown(f"**Observation** : {r.get('observation')}")
            st.markdown(f"**Action** : {r.get('action')}")

with tab4:
    cols = st.columns(3)
    for i, (svc, stats) in enumerate(services.items()):
        pct = stats["availability"]
        color = "#28a745" if pct >= 99 else "#fd7e14" if pct >= 95 else "#dc3545"
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number", value=pct,
            title={"text": svc},
            number={"suffix": "%"},
            gauge={"axis": {"range": [80, 100]}, "bar": {"color": color},
                   "threshold": {"line": {"color": "red", "width": 3}, "value": 99}},
        ))
        fig_g.update_layout(height=220, margin=dict(t=30, b=10, l=20, r=20))
        cols[i].plotly_chart(fig_g, width="stretch")
        cols[i].caption(f"✅ {stats['online']} online · ⚠️ {stats['degraded']} dégradés · 🔴 {stats['offline']} offline")

with tab5:
    from datetime import datetime
    st.download_button(
        "⬇️ Télécharger le rapport",
        data=json.dumps(report, ensure_ascii=False, indent=2),
        file_name=f"rapport_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
    )
    st.json(report)
