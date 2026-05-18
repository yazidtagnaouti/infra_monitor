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
from nodes.anomaly import THRESHOLDS

SEVERITY_COLORS = {
    "critical": "#C62828",
    "warning": "#EF6C00",
}
SEVERITY_LABELS = {
    "critical": "Critique",
    "warning": "Warning",
}
SEVERITY_COLOR_MAP = {
    **SEVERITY_COLORS,
    "Critique": SEVERITY_COLORS["critical"],
    "Critiques": SEVERITY_COLORS["critical"],
    "Warning": SEVERITY_COLORS["warning"],
    "Warnings": SEVERITY_COLORS["warning"],
}

st.set_page_config(page_title="Infrastructure Monitor", layout="wide")

# Inject Streamlit Cloud secrets into env
try:
    if "GROQ_API_KEY" in st.secrets:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Infra Monitor")
    uploaded = st.file_uploader("Fichier JSON", type=["json"])

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        api_key = st.text_input("Groq API Key", type="password", placeholder="gsk_...")
        if api_key:
            os.environ["GROQ_API_KEY"] = api_key
    else:
        st.success("Clé API détectée")

    run = st.button("Lancer le pipeline", type="primary", width="stretch")


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
    st.info("Chargez un fichier JSON puis cliquez **Lancer le pipeline**.")
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Métriques", "Anomalies", "Recommandations", "Services", "JSON"])

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
    all_anomalies = []
    for r in records:
        for metric, levels in THRESHOLDS.items():
            val = r.get(metric)
            if val is None:
                continue
            if val >= levels["crit"]:
                all_anomalies.append(
                    {"Timestamp": r["timestamp"], "Métrique": metric, "Valeur": val, "Sévérité": "critical"}
                )
            elif val >= levels["warn"]:
                all_anomalies.append(
                    {"Timestamp": r["timestamp"], "Métrique": metric, "Valeur": val, "Sévérité": "warning"}
                )
        for svc, status in r.get("service_status", {}).items():
            if status == "online":
                continue
            sev = "critical" if status == "offline" else "warning"
            all_anomalies.append(
                {
                    "Timestamp": r["timestamp"],
                    "Métrique": f"service_{svc}",
                    "Valeur": status,
                    "Sévérité": sev,
                }
            )

    bar_rows = []
    for a in all_anomalies:
        bar_rows.append(
            {
                "Métrique": a["Métrique"],
                "Sévérité": SEVERITY_LABELS[a["Sévérité"]],
                "count": 1,
            }
        )
    df_bar = (
        pd.DataFrame(bar_rows)
        .groupby(["Métrique", "Sévérité"], as_index=False)["count"]
        .sum()
        .sort_values("count", ascending=True)
    )

    c1, c2 = st.columns(2)
    with c1:
        fig_b = px.bar(
            df_bar,
            x="count",
            y="Métrique",
            color="Sévérité",
            orientation="h",
            title="Anomalies par métrique",
            color_discrete_map=SEVERITY_COLOR_MAP,
            category_orders={"Sévérité": ["Warning", "Critique"]},
        )
        fig_b.update_layout(
            barmode="stack",
            legend_title="Sévérité",
            coloraxis_showscale=False,
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_b, width="stretch")
    with c2:
        fig_p = go.Figure(
            go.Pie(
                labels=["Critiques", "Warnings"],
                values=[anom["critical"], anom["warning"]],
                marker={"colors": [SEVERITY_COLORS["critical"], SEVERITY_COLORS["warning"]]},
                hole=0.5,
            )
        )
        fig_p.update_layout(title="Répartition par sévérité", height=300)
        st.plotly_chart(fig_p, width="stretch")

    sev_filter = st.multiselect(
        "Sévérité",
        ["critical", "warning"],
        default=["critical", "warning"],
        format_func=lambda s: SEVERITY_LABELS[s],
    )
    filtered = [a for a in all_anomalies if a["Sévérité"] in sev_filter]
    df_anom = pd.DataFrame(filtered)
    if not df_anom.empty:
        df_anom = df_anom.assign(
            Sévérité=df_anom["Sévérité"].map(SEVERITY_LABELS)
        )

        def _severity_style(val):
            color = SEVERITY_COLOR_MAP.get(val, "")
            if not color:
                return ""
            return f"background-color: {color}; color: #FFFFFF; font-weight: 600"

        styled = df_anom.style.map(_severity_style, subset=["Sévérité"])
        st.dataframe(styled, width="stretch", height=300, hide_index=True)
    else:
        st.dataframe(df_anom, width="stretch", height=300, hide_index=True)

with tab3:
    llm = bool(os.getenv("GROQ_API_KEY"))
    st.caption(
        "Recommandations via Groq (LLM)"
        if llm
        else "Règles Python — ajoutez une clé Groq (config.py ou sidebar) pour l'enrichissement IA"
    )
    for r in recos:
        with st.expander(
            f"[{r.get('priority')}] [{r.get('id')}] {r.get('title')}",
            expanded=(r.get("priority") == "Critique"),
        ):
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
            mode="gauge+number",
            value=pct,
            title={"text": svc, "align": "center"},
            number={"suffix": "%"},
            gauge={
                "axis": {"range": [80, 100]},
                "bar": {"color": color},
                "threshold": {"line": {"color": "red", "width": 3}, "value": 99},
            },
        ))
        fig_g.update_layout(
            height=220,
            margin=dict(t=40, b=20, l=30, r=30),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        with cols[i]:
            st.plotly_chart(fig_g, width="stretch")
            st.markdown(
                f"<p style='text-align:center;margin:0.25rem 0 0;'>"
                f"{stats['online']} online · {stats['degraded']} dégradés · "
                f"{stats['offline']} offline</p>",
                unsafe_allow_html=True,
            )

with tab5:
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    summary = report.get("analysis_summary") or {}

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Synthèse d'analyse (JSON)",
            data=json.dumps(summary, ensure_ascii=False, indent=2),
            file_name=f"analysis_summary_{ts}.json",
            mime="application/json",
        )
    with c2:
        st.download_button(
            "Rapport complet (JSON)",
            data=json.dumps(report, ensure_ascii=False, indent=2),
            file_name=f"rapport_{ts}.json",
            mime="application/json",
        )

    st.subheader("Synthèse d'analyse")
    st.json(summary)
    st.subheader("Rapport complet")
    st.json(report)
