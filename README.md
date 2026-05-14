# Infrastructure Monitor — Pipeline LangGraph + Dashboard Streamlit

Solution pour Jean (CTO) — Analyse d'infrastructure, détection d'anomalies, recommandations IA.

## Stack technique

| Composant | Outil | Tier |
|---|---|---|
| Orchestration pipeline | **LangGraph** | Open source |
| Dashboard | **Streamlit** | Free tier |
| LLM recommandations | **Claude Haiku 4.5** (Anthropic) | Free tier |
| Visualisations | **Plotly** | Open source |

## Architecture — 5 nœuds séquentiels

```
data.json (input)
    │
    ▼
Nœud 1 · ingestion_node   → Lecture + validation JSON
    │
    ▼
Nœud 2 · analysis_node    → avg / min / max / p95 par métrique
    │
    ▼
Nœud 3 · anomaly_node     → Seuils warning/critical + état services
    │
    ▼
Nœud 4 · reco_node        → Claude Haiku (ou règles Python si pas de clé)
    │
    ▼
Nœud 5 · report_node      → Rapport JSON + health score
    │
    ▼
Dashboard Streamlit (affichage)
```

## Installation locale

```bash
# 1. Cloner le projet
git clone https://github.com/votre-repo/infra-monitor.git
cd infra-monitor

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. (Optionnel) Configurer la clé Claude
export ANTHROPIC_API_KEY="sk-ant-..."
# Ou la saisir directement dans la sidebar du dashboard

# 4. Lancer le dashboard
streamlit run app.py
```

Ouvrir http://localhost:8501

## Déploiement sur Streamlit Cloud (gratuit)

1. **Pusher le projet sur GitHub** (repo public ou privé)
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/votre-user/infra-monitor.git
   git push -u origin main
   ```

2. **Connecter sur Streamlit Cloud**
   - Aller sur https://share.streamlit.io
   - New app → sélectionner votre repo → `app.py`
   - Cliquer **Deploy**

3. **Ajouter la clé API Claude**
   - Dans Streamlit Cloud : **Settings → Secrets**
   - Coller :
     ```toml
     ANTHROPIC_API_KEY = "sk-ant-xxxxxxxxxx"
     ```

4. **Charger vos données**
   - Uploader votre `data.json` depuis la sidebar
   - Cliquer **Lancer le pipeline**

## Obtenir une clé Claude gratuite

1. Aller sur https://console.anthropic.com
2. Créer un compte
3. API Keys → **Create Key**
4. Le free tier inclut un crédit de démarrage (suffisant pour ce projet)

## Format du fichier JSON d'entrée

```json
[
  {
    "timestamp": "2023-10-01T12:00:00Z",
    "cpu_usage": 85,
    "memory_usage": 70,
    "latency_ms": 250,
    "disk_usage": 65,
    "network_in_kbps": 1200,
    "network_out_kbps": 900,
    "io_wait": 5,
    "thread_count": 150,
    "active_connections": 45,
    "error_rate": 0.02,
    "uptime_seconds": 360000,
    "temperature_celsius": 65,
    "power_consumption_watts": 250,
    "service_status": {
      "database": "online",
      "api_gateway": "degraded",
      "cache": "online"
    }
  }
]
```

## Structure du projet

```
infra_monitor/
├── app.py                    # Dashboard Streamlit (point d'entrée)
├── pipeline.py               # Compilation du graphe LangGraph
├── state.py                  # InfraState — état partagé (TypedDict)
├── data.json                 # Données d'exemple
├── requirements.txt          # Dépendances Python
├── .gitignore
├── .streamlit/
│   ├── config.toml           # Thème Streamlit
│   └── secrets.toml          # Clés API (NE PAS committer)
└── nodes/
    ├── ingestion.py          # Nœud 1
    ├── analysis.py           # Nœud 2
    ├── anomaly.py            # Nœud 3
    ├── reco.py               # Nœud 4 — Claude Haiku / fallback règles
    └── report.py             # Nœud 5
```
