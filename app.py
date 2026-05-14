"""
app.py — Dashboard Streamlit : Infrastructure Monitor

Lancement local    : streamlit run app.py
Déploiement Cloud  : https://share.streamlit.io
                     → connecter le repo GitHub + ajouter ANTHROPIC_API_KEY dans Settings > Secrets

Clé API Claude :
  - Local        : variable d'environnement ANTHROPIC_API_KEY ou saisie dans la sidebar
  - Streamlit Cloud : Settings → Secrets → ANTHROPIC_API_KEY = "sk-ant-..."
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# Injecter st.secrets dans os.environ pour que nodes/reco.py les lise
import streamlit as st
try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass  # Pas de secrets configurés (normal en local)

import json
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
from pipeline import build_pipeline

# ── Configuration de la page ────────────────────────────────────────────────
st.set_page_config(
    page_title="Infrastructure Monitor",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS personnalisé ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 16px 20px;
        border-left: 4px solid #6c757d;
        margin-bottom: 8px;
    }
    .metric-card.critical { border-left-color: #dc3545; background: #fff5f5; }
    .metric-card.warning  { border-left-color: #fd7e14; background: #fff8f0; }
    .metric-card.ok       { border-left-color: #28a745; background: #f0fff4; }
    .reco-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 10px;
        background: white;
    }
    .pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
    }
    .pill-critique { background: #ffe0e0; color: #c0392b; }
    .pill-haute    { background: #fff3e0; color: #d35400; }
    .pill-moyenne  { background: #e8f4fd; color: #2980b9; }
    .health-score {
        font-size: 64px;
        font-weight: 700;
        text-align: center;
        line-height: 1;
    }
    .node-badge {
        display: inline-block;
        background: #e8f0fe;
        color: #1a73e8;
        border-radius: 6px;
        padding: 3px 10px;
        font-size: 12px;
        font-weight: 500;
        margin: 2px;
    }
    .node-badge.done { background: #e6f4ea; color: #137333; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def run_pipeline(records_json: str, _api_key: str):
    """Cache le résultat — relancé uniquement si les données changent."""
    records = json.loads(records_json)
    app = build_pipeline()
    return app.invoke({"records": records})


def health_color(score):
    if score >= 80: return "#28a745"
    if score >= 60: return "#fd7e14"
    return "#dc3545"


def severity_icon(sev):
    return "🔴" if sev == "critical" else "🟡"


def priority_pill(priority):
    cls = {"Critique": "critique", "Haute": "haute", "Moyenne": "moyenne"}.get(priority, "moyenne")
    return f'<span class="pill pill-{cls}">{priority}</span>'


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/server.png", width=60)
    st.title("Infrastructure Monitor")
    st.caption("Pipeline LangGraph + Streamlit")

    st.divider()
    st.subheader("📁 Source de données")
    uploaded = st.file_uploader("Fichier JSON de métriques", type=["json"])

    st.subheader("🤖 Claude API (optionnel)")

    # En local : saisie manuelle. Sur Streamlit Cloud : lu depuis st.secrets
    env_key = os.getenv("ANTHROPIC_API_KEY", "")
    if env_key:
        st.success("✅ Clé API détectée (secrets / env)")
        anthropic_key = env_key
    else:
        anthropic_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="Gratuit sur console.anthropic.com — sans clé : règles Python pures",
        )
        if anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_key

    with st.expander("ℹ️ Déploiement Streamlit Cloud"):
        st.caption(
            "1. Pushez ce projet sur GitHub\n"
            "2. Connectez-le sur share.streamlit.io\n"
            "3. Settings → **Secrets** → ajoutez :\n"
            "```\nANTHROPIC_API_KEY = \"sk-ant-...\"\n```"
        )

    st.divider()
    run_btn = st.button("▶ Lancer le pipeline", type="primary", use_container_width=True)

    st.divider()
    st.caption("**Stack technique**")
    st.caption("• LangGraph — orchestration")
    st.caption("• Claude Haiku 4.5 — LLM free tier")
    st.caption("• Streamlit — dashboard")
    st.caption("• Plotly — visualisations")


# ── Chargement des données ────────────────────────────────────────────────────
if uploaded:
    raw_records = json.load(uploaded)
elif os.path.exists(os.path.join(os.path.dirname(__file__), "data.json")):
    with open(os.path.join(os.path.dirname(__file__), "data.json"), encoding="utf-8") as f:
        raw_records = json.load(f)
else:
    raw_records = None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🖥️ Infrastructure Monitor — Jean (CTO)")
st.markdown("Pipeline modulaire d'analyse · Détection d'anomalies · Recommandations IA")

# ── Pipeline status bar ───────────────────────────────────────────────────────
nodes = ["Nœud 1 · Ingestion", "Nœud 2 · Analyse", "Nœud 3 · Anomalies",
         "Nœud 4 · Recommandations", "Nœud 5 · Rapport"]

if "report" not in st.session_state:
    cols = st.columns(len(nodes))
    for i, (col, node) in enumerate(zip(cols, nodes)):
        col.markdown(f'<span class="node-badge">⬜ {node}</span>', unsafe_allow_html=True)
    st.info("⬆️ Chargez un fichier JSON ou utilisez data.json, puis cliquez **Lancer le pipeline**.")
else:
    cols = st.columns(len(nodes))
    for col, node in zip(cols, nodes):
        col.markdown(f'<span class="node-badge done">✅ {node}</span>', unsafe_allow_html=True)

st.divider()

# ── Lancement du pipeline ─────────────────────────────────────────────────────
if run_btn:
    if not raw_records:
        st.error("Aucune donnée disponible. Chargez un fichier JSON.")
        st.stop()

    with st.status("Exécution du pipeline LangGraph…", expanded=True) as status:
        step_labels = [
            ("ingestion",  "Nœud 1 · Ingestion des données"),
            ("analysis",   "Nœud 2 · Analyse des métriques"),
            ("anomaly",    "Nœud 3 · Détection d'anomalies"),
            ("reco",       "Nœud 4 · Génération des recommandations"),
            ("report",     "Nœud 5 · Assemblage du rapport"),
        ]
        for _, label in step_labels:
            st.write(f"⚙️ {label}…")

        result = run_pipeline(json.dumps(raw_records), os.getenv("ANTHROPIC_API_KEY", ""))
        st.session_state["report"] = result["report"]
        st.session_state["records"] = raw_records
        status.update(label="✅ Pipeline terminé !", state="complete")
    st.rerun()

# ── Dashboard principal ───────────────────────────────────────────────────────
if "report" in st.session_state:
    report  = st.session_state["report"]
    records = st.session_state["records"]
    metrics = report["metrics_summary"]
    svc     = report["service_availability"]
    anomalies = report["anomalies"]
    recos   = report["recommendations"]
    summary = report["anomalies_summary"]
    df      = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # ── KPI Cards ────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)

    score = report["health_score"]
    score_color = health_color(score)
    k1.markdown(f"""
    <div style="text-align:center;padding:12px;background:#f8f9fa;border-radius:12px">
        <div style="font-size:12px;color:#666;margin-bottom:4px">Health Score</div>
        <div style="font-size:48px;font-weight:700;color:{score_color};line-height:1">{score}</div>
        <div style="font-size:12px;color:#666">/100</div>
    </div>""", unsafe_allow_html=True)

    cpu_p95 = metrics.get("cpu_usage", {}).get("p95", 0)
    cpu_cls = "critical" if cpu_p95 > 85 else "warning" if cpu_p95 > 70 else "ok"
    k2.markdown(f"""
    <div class="metric-card {cpu_cls}">
        <div style="font-size:12px;color:#666">CPU p95</div>
        <div style="font-size:28px;font-weight:700">{cpu_p95}%</div>
        <div style="font-size:11px;color:#999">max {metrics.get("cpu_usage",{}).get("max",0)}%</div>
    </div>""", unsafe_allow_html=True)

    ram_p95 = metrics.get("memory_usage", {}).get("p95", 0)
    ram_cls = "critical" if ram_p95 > 85 else "warning" if ram_p95 > 75 else "ok"
    k3.markdown(f"""
    <div class="metric-card {ram_cls}">
        <div style="font-size:12px;color:#666">RAM p95</div>
        <div style="font-size:28px;font-weight:700">{ram_p95}%</div>
        <div style="font-size:11px;color:#999">max {metrics.get("memory_usage",{}).get("max",0)}%</div>
    </div>""", unsafe_allow_html=True)

    lat_p95 = metrics.get("latency_ms", {}).get("p95", 0)
    lat_cls = "critical" if lat_p95 > 300 else "warning" if lat_p95 > 200 else "ok"
    k4.markdown(f"""
    <div class="metric-card {lat_cls}">
        <div style="font-size:12px;color:#666">Latence p95</div>
        <div style="font-size:28px;font-weight:700">{lat_p95}ms</div>
        <div style="font-size:11px;color:#999">max {metrics.get("latency_ms",{}).get("max",0)}ms</div>
    </div>""", unsafe_allow_html=True)

    k5.markdown(f"""
    <div class="metric-card {'critical' if summary['critical'] > 0 else 'ok'}">
        <div style="font-size:12px;color:#666">Anomalies</div>
        <div style="font-size:28px;font-weight:700">{summary['total']}</div>
        <div style="font-size:11px;color:#dc3545">{summary['critical']} critiques</div>
    </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Onglets ───────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Métriques", "🚨 Anomalies", "💡 Recommandations",
        "🔧 Services", "📄 Rapport JSON"
    ])

    # ── TAB 1 : Métriques ─────────────────────────────────────────────────────
    with tab1:
        st.subheader("Évolution temporelle des métriques")

        col_a, col_b = st.columns(2)

        with col_a:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["timestamp"], y=df["cpu_usage"],
                name="CPU %", line=dict(color="#e74c3c", width=2)))
            fig.add_trace(go.Scatter(x=df["timestamp"], y=df["memory_usage"],
                name="RAM %", line=dict(color="#3498db", width=2, dash="dot")))
            fig.add_hline(y=85, line_dash="dash", line_color="#e74c3c",
                annotation_text="Seuil critique 85%", annotation_position="bottom right")
            fig.update_layout(title="CPU & RAM (%)", height=300,
                margin=dict(t=40, b=20, l=20, r=20), legend=dict(orientation="h"))
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df["timestamp"], y=df["latency_ms"],
                name="Latence ms", line=dict(color="#9b59b6", width=2), fill="tozeroy",
                fillcolor="rgba(155,89,182,0.1)"))
            fig2.add_hline(y=300, line_dash="dash", line_color="#e74c3c",
                annotation_text="Seuil critique 300ms")
            fig2.update_layout(title="Latence réseau (ms)", height=300,
                margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig2, use_container_width=True)

        col_c, col_d = st.columns(2)

        with col_c:
            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=df["timestamp"], y=df["disk_usage"],
                name="Disque %", line=dict(color="#e67e22", width=2)))
            fig3.add_trace(go.Scatter(x=df["timestamp"], y=df["temperature_celsius"],
                name="Temp °C", line=dict(color="#e74c3c", width=2, dash="dot")))
            fig3.add_hline(y=85, line_dash="dash", line_color="#aaa",
                annotation_text="Seuil 85")
            fig3.update_layout(title="Disque (%) & Température (°C)", height=300,
                margin=dict(t=40, b=20, l=20, r=20), legend=dict(orientation="h"))
            st.plotly_chart(fig3, use_container_width=True)

        with col_d:
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(x=df["timestamp"], y=df["error_rate"],
                name="Error rate", line=dict(color="#c0392b", width=2), fill="tozeroy",
                fillcolor="rgba(192,57,43,0.1)"))
            fig4.add_hline(y=0.08, line_dash="dash", line_color="#e74c3c",
                annotation_text="Seuil critique 0.08")
            fig4.update_layout(title="Taux d'erreur", height=300,
                margin=dict(t=40, b=20, l=20, r=20))
            st.plotly_chart(fig4, use_container_width=True)

        # Tableau des statistiques
        st.subheader("Tableau récapitulatif des métriques")
        stat_rows = []
        for m, s in metrics.items():
            stat_rows.append({"Métrique": m, "Moyenne": s["avg"],
                               "Min": s["min"], "Max": s["max"], "P95": s["p95"]})
        st.dataframe(pd.DataFrame(stat_rows), use_container_width=True, hide_index=True)

    # ── TAB 2 : Anomalies ─────────────────────────────────────────────────────
    with tab2:
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.subheader("Répartition des anomalies")
            by_metric = summary["by_metric"]
            fig_bar = px.bar(
                x=list(by_metric.values()),
                y=list(by_metric.keys()),
                orientation="h",
                color=list(by_metric.values()),
                color_continuous_scale=["#28a745", "#fd7e14", "#dc3545"],
                labels={"x": "Nombre d'événements", "y": "Métrique"},
            )
            fig_bar.update_layout(height=350, margin=dict(t=20, b=20, l=20, r=20),
                                  showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_right:
            st.subheader("Sévérité")
            fig_pie = go.Figure(go.Pie(
                labels=["Critiques", "Warnings"],
                values=[summary["critical"], summary["warning"]],
                marker_colors=["#dc3545", "#fd7e14"],
                hole=0.55,
            ))
            fig_pie.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.15))
            st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader(f"Liste des anomalies ({len(anomalies)} événements)")

        # Filtres
        fc1, fc2 = st.columns(2)
        sev_filter = fc1.multiselect("Sévérité", ["critical", "warning"],
                                      default=["critical", "warning"])
        metric_filter = fc2.multiselect("Métrique", list(by_metric.keys()),
                                         default=list(by_metric.keys())[:5])

        filtered = [a for a in anomalies
                    if a["severity"] in sev_filter
                    and a["metric"] in metric_filter]

        anom_df = pd.DataFrame(filtered)[["timestamp","metric","value","severity","message"]]
        anom_df.columns = ["Timestamp", "Métrique", "Valeur", "Sévérité", "Message"]

        def color_severity(val):
            if val == "critical": return "background-color: #fff5f5; color: #c0392b"
            return "background-color: #fff8f0; color: #d35400"

        st.dataframe(
            anom_df.style.map(color_severity, subset=["Sévérité"]),
            use_container_width=True, height=350,
        )

    # ── TAB 3 : Recommandations ───────────────────────────────────────────────
    with tab3:
        llm_used = bool(os.getenv("ANTHROPIC_API_KEY"))
        if llm_used:
            st.success("✅ Recommandations générées par **Claude Haiku 4.5** (Anthropic free tier)")
        else:
            st.info("ℹ️ Recommandations par règles Python — ajoutez une **Anthropic API Key** dans la sidebar pour l'enrichissement IA")

        for r in recos:
            priority = r.get("priority", "Moyenne")
            icon = "🔴" if priority == "Critique" else "🟠" if priority == "Haute" else "🔵"
            with st.expander(f"{icon} [{r['id']}] {r['title']}", expanded=(priority == "Critique")):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Priorité** : {priority_pill(priority)}", unsafe_allow_html=True)
                c2.markdown(f"**Effort** : `{r.get('effort','—')}`")
                c3.markdown(f"**Impact** : {r.get('impact','—')}")
                st.markdown(f"**Observation** : {r.get('observation','')}")
                st.markdown("**Action recommandée :**")
                action_text = r.get("action", "")
                for line in action_text.split(". "):
                    line = line.strip()
                    if line:
                        st.markdown(f"- {line}")

    # ── TAB 4 : Services ─────────────────────────────────────────────────────
    with tab4:
        st.subheader("Disponibilité des services")

        svc_cols = st.columns(3)
        for i, (service, stats) in enumerate(svc.items()):
            pct = stats["availability_pct"]
            color = "#28a745" if pct >= 99 else "#fd7e14" if pct >= 95 else "#dc3545"
            with svc_cols[i]:
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=pct,
                    title={"text": service},
                    number={"suffix": "%", "font": {"size": 28}},
                    gauge={
                        "axis": {"range": [80, 100]},
                        "bar": {"color": color},
                        "steps": [
                            {"range": [80, 95], "color": "#fff5f5"},
                            {"range": [95, 99], "color": "#fff8f0"},
                            {"range": [99, 100], "color": "#f0fff4"},
                        ],
                        "threshold": {"line": {"color": "#dc3545", "width": 3},
                                      "thickness": 0.75, "value": 99},
                    },
                ))
                fig_gauge.update_layout(height=220, margin=dict(t=30, b=10, l=20, r=20))
                st.plotly_chart(fig_gauge, use_container_width=True)
                st.markdown(f"""
                <div style="text-align:center;font-size:13px">
                    ✅ {stats['online']} online &nbsp;
                    ⚠️ {stats['degraded']} dégradés &nbsp;
                    🔴 {stats['offline']} offline
                </div>""", unsafe_allow_html=True)

        # Timeline des statuts
        st.subheader("Timeline des incidents")
        svc_cols2 = ["database", "api_gateway", "cache"]
        status_map = {"online": 1, "degraded": 0.5, "offline": 0}
        fig_svc = go.Figure()
        colors = {"online": "#28a745", "degraded": "#fd7e14", "offline": "#dc3545"}

        for svc_name in svc_cols2:
            statuses = [r["service_status"].get(svc_name, "online") for r in records]
            vals = [status_map.get(s, 1) for s in statuses]
            fig_svc.add_trace(go.Scatter(
                x=df["timestamp"], y=[svc_cols2.index(svc_name) + v * 0.8 for v in vals],
                name=svc_name, mode="lines",
                line=dict(width=8),
                hovertemplate="%{text}<extra></extra>",
                text=statuses,
            ))

        fig_svc.update_layout(
            height=200, margin=dict(t=20, b=20, l=20, r=20),
            yaxis=dict(tickvals=[0.4, 1.4, 2.4], ticktext=svc_cols2),
        )
        st.plotly_chart(fig_svc, use_container_width=True)

    # ── TAB 5 : JSON ─────────────────────────────────────────────────────────
    with tab5:
        st.subheader("Rapport JSON complet")
        report_export = {k: v for k, v in report.items() if k != "anomalies"}
        report_export["anomalies_sample"] = report["anomalies"][:10]
        report_json = json.dumps(report_export, ensure_ascii=False, indent=2)

        st.download_button(
            "⬇️ Télécharger le rapport complet",
            data=json.dumps(report, ensure_ascii=False, indent=2),
            file_name=f"rapport_infra_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
        )
        st.code(report_json[:4000] + ("\n…" if len(report_json) > 4000 else ""),
                language="json")

else:
    # État initial : placeholder
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;color:#999">
        <div style="font-size:64px">🖥️</div>
        <div style="font-size:20px;margin-top:16px;font-weight:500">
            Chargez vos données et lancez le pipeline
        </div>
        <div style="font-size:14px;margin-top:8px">
            Utilisez le panneau latéral → <strong>Lancer le pipeline</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)
