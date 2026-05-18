# Infrastructure Monitor

Petit outil maison : tu balances un JSON de métriques infra, un pipeline LangGraph fait le boulot (stats, anomalies, reco), Streamlit affiche le reste.

Stack : LangGraph, Streamlit, Plotly, Groq (optionnel pour les recommandations).

## Pipeline

Le flux c'est ingestion → analyse → détection d'anomalies → recommandations → rapport. Tout passe par un état partagé (`InfraState` dans `state.py`). Le détail est dans `pipeline.py` et le dossier `nodes/`.

## Lancer en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Clé Groq si tu veux les recos LLM : copier `config.example.py` → `config.py` et remplir `GROQ_API_KEY`, ou variable d'env / sidebar.

## Format JSON

Tableau d'objets avec au minimum `timestamp`, les métriques (cpu, ram, latence, etc.) et `service_status` :

```json
[
  {
    "timestamp": "2023-10-01T12:00:00Z",
    "cpu_usage": 85,
    "memory_usage": 70,
    "latency_ms": 250,
    "service_status": {
      "database": "online",
      "api_gateway": "degraded",
      "cache": "online"
    }
  }
]
```

`data.json` à la racine = exemple.

## Seuils anomalies (repère rapide)

| Métrique | Warning | Critical |
|----------|---------|----------|
| CPU | 70 % | 85 % |
| RAM | 75 % | 85 % |
| Latence | 200 ms | |
| Disque | 75 % | 85 % |

(Les autres seuils sont dans `nodes/anomaly.py`.)

## Structure

```
infra_monitor/
├── app.py
├── pipeline.py
├── state.py
├── data.json
└── nodes/
    ├── ingestion.py
    ├── analysis.py
    ├── anomaly.py
    ├── reco.py
    └── report.py
```

## Déploiement

Devrait tourner sur Streamlit Cloud (`app.py` + secrets pour `GROQ_API_KEY` si besoin). Ça a marché pour moi, ymmv.

## Known issues / limitations

- Pas de validation sérieuse si le JSON est vide ou mal formé (ça plantera probablement sur `records[0]`).
- La liste des services est en dur (`database`, `api_gateway`, `cache`).
- Le health score est une heuristique grossière, pas un vrai SLO.
- Sans clé Groq tu tombes sur les règles Python — c'est voulu mais moins riche.
