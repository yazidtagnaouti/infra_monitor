# Infrastructure Monitor — Pipeline LangGraph + Dashboard Streamlit

Solution pour Jean (CTO) — Analyse d'infrastructure, détection d'anomalies, recommandations IA.

## Stack technique

| Composant | Outil | Tier |
|---|---|---|
| Orchestration pipeline | **LangGraph** | Open source |
| Dashboard | **Streamlit** | Free tier |
| LLM recommandations | **Groq** (Llama, etc.) | Free tier |
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
Nœud 4 · reco_node        → Groq (ou règles Python si pas de clé)
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

# 3. (Optionnel) Clé Groq — fichier local config.py (gitignoré) ou variable d'environnement
export GROQ_API_KEY="gsk_..."
# Optionnel : export GROQ_MODEL="llama-3.3-70b-versatile"
# Ou saisir la clé dans la sidebar du dashboard

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

3. **Ajouter la clé API Groq**
   - Dans Streamlit Cloud : **Settings → Secrets**
   - Coller :
     ```toml
     GROQ_API_KEY = "gsk_xxxxxxxxxx"
     ```

4. **Charger vos données**
   - Uploader votre `data.json` depuis la sidebar
   - Cliquer **Lancer le pipeline**

## Obtenir une clé Groq

1. Aller sur https://console.groq.com
2. Créer un compte
3. **API Keys** → créer une clé (`gsk_...`)
4. Choisir un modèle (défaut dans le code : `llama-3.3-70b-versatile`, surcharge possible avec `GROQ_MODEL`)

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
    ├── reco.py               # Nœud 4 — Groq / fallback règles
    └── report.py             # Nœud 5
```
