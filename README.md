# Infrastructure Monitor

Outil de supervision d'infrastructure : il lit des mesures serveur (JSON), les analyse, détecte les problèmes, propose des actions correctives, puis affiche le tout dans un tableau de bord web.

## En bref

1. Vous fournissez un fichier JSON avec des instantanés de monitoring (CPU, RAM, latence, etc.).
2. Un **pipeline** en 5 étapes traite ces données l'une après l'autre.
3. Un **dashboard Streamlit** affiche le score de santé, les graphiques, les anomalies et les recommandations.

Technologies : **LangGraph** (enchaînement des étapes), **Streamlit** (interface), **Groq** (recommandations IA, optionnel), **Plotly** (graphiques).

## Fonctionnement du pipeline

```
Fichier JSON
     │
     ▼
┌─────────────┐
│  Ingestion  │  Lecture des données
└──────┬──────┘
       ▼
┌─────────────┐
│  Analyse    │  Statistiques par métrique
└──────┬──────┘
       ▼
┌─────────────┐
│  Anomalies  │  Détection des dépassements
└──────┬──────┘
       ▼
┌─────────────┐
│  Reco       │  Conseils (IA ou règles)
└──────┬──────┘
       ▼
┌─────────────┐
│  Rapport    │  Synthèse + score de santé
└──────┬──────┘
       ▼
  Dashboard Streamlit
```

Chaque étape lit et enrichit un **état partagé** (`InfraState`) : enregistrements, métriques, services, anomalies, recommandations, rapport final.

---

### Nœud 1 — Ingestion (`nodes/ingestion.py`)

Charge le fichier JSON (par défaut `data.json`, ou un fichier uploadé dans le dashboard).

**Sortie :** la liste des enregistrements (`records`), un objet par instant avec timestamp, métriques et statut des services.

---

### Nœud 2 — Analyse (`nodes/analysis.py`)

Parcourt tous les enregistrements et calcule, pour chaque métrique (CPU, RAM, latence, disque, erreurs, température, I/O wait) :

| Indicateur | Signification |
|------------|----------------|
| **avg** | Valeur moyenne |
| **min** | Valeur la plus basse |
| **max** | Pic le plus haut |
| **p95** | 95 % des mesures sont en dessous de cette valeur |

Calcule aussi la **disponibilité** des services (`database`, `api_gateway`, `cache`) : nombre de fois online / degraded / offline et pourcentage de disponibilité.

**Sortie :** `metrics` et `services`.

---

### Nœud 3 — Anomalies (`nodes/anomaly.py`)

Compare chaque mesure aux **seuils** définis (warning et critical). Exemples :

| Métrique | Warning | Critical |
|----------|---------|----------|
| CPU | 70 % | 85 % |
| RAM | 75 % | 85 % |
| Latence | 200 ms | 300 ms |
| Disque | 75 % | 85 % |
| Taux d'erreur | 0,03 | 0,08 |
| Température | 70 °C | 80 °C |

Si un service n'est pas `online` (`degraded` ou `offline`), une anomalie est aussi enregistrée.

**Sortie :** liste d'anomalies avec horodatage, métrique, valeur et sévérité.

---

### Nœud 4 — Recommandations (`nodes/reco.py`)

Produit entre 3 et 8 actions concrètes à partir des métriques, services et anomalies.

- **Avec clé API Groq :** envoi d'un résumé au modèle LLM (par défaut `llama-3.3-70b-versatile`), qui renvoie des recommandations structurées (priorité, observation, action, effort, impact).
- **Sans clé :** règles Python de secours (ex. CPU p95 > 80 % → saturation CPU, latence p95 > 250 ms → optimiser le cache, etc.).

En cas d'erreur API ou de réponse invalide, le mode règles est utilisé automatiquement.

**Sortie :** `recommendations`.

---

### Nœud 5 — Rapport (`nodes/report.py`)

Assemble le rapport final :

- Période couverte (premier et dernier timestamp)
- Nombre d'enregistrements
- **Health score** (0–100) : 100 moins des pénalités si CPU, RAM ou disque (p95) dépassent 70 %
- Métriques, services, résumé des anomalies (total, critiques, warnings, par métrique)
- Liste des recommandations

**Sortie :** `report` (téléchargeable en JSON depuis le dashboard).

---

## Dashboard (`app.py`)

Après avoir chargé un JSON et cliqué sur **Lancer le pipeline**, l'interface affiche :

- **KPIs** : health score, p95 CPU/RAM/latence, nombre d'anomalies
- **Métriques** : courbes temporelles et tableau récapitulatif
- **Anomalies** : graphiques et tableau filtrable
- **Recommandations** : fiches détaillées par priorité
- **Services** : jauges de disponibilité
- **JSON** : rapport complet exportable

---

## Installation

```bash
git clone <url-du-repo>
cd infra_monitor
pip install -r requirements.txt
streamlit run app.py
```

Ouvrir http://localhost:8501

### Clé Groq (optionnelle)

Pour des recommandations générées par IA :

```bash
cp config.example.py config.py
# Renseigner GROQ_API_KEY dans config.py
```

Ou : variable d'environnement `GROQ_API_KEY`, saisie dans la sidebar du dashboard, ou secret Streamlit Cloud.

Clé disponible sur https://console.groq.com — modèle surchargeable via `GROQ_MODEL`.

---

## Format du fichier JSON

Tableau d'objets ; chaque objet = un instant de mesure :

```json
[
  {
    "timestamp": "2023-10-01T12:00:00Z",
    "cpu_usage": 85,
    "memory_usage": 70,
    "latency_ms": 250,
    "disk_usage": 65,
    "io_wait": 5,
    "error_rate": 0.02,
    "temperature_celsius": 65,
    "service_status": {
      "database": "online",
      "api_gateway": "degraded",
      "cache": "online"
    }
  }
]
```

Un fichier `data.json` d'exemple est fourni à la racine du projet.

---

## Structure du projet

```
infra_monitor/
├── app.py              # Dashboard Streamlit
├── pipeline.py         # Graphe LangGraph (5 nœuds)
├── state.py            # État partagé du pipeline
├── data.json           # Données d'exemple
├── config.example.py   # Modèle pour la clé Groq
├── requirements.txt
└── nodes/
    ├── ingestion.py
    ├── analysis.py
    ├── anomaly.py
    ├── reco.py
    └── report.py
```

---

## Déploiement Streamlit Cloud

1. Pousser le dépôt sur GitHub.
2. Créer une app sur https://share.streamlit.io → fichier `app.py`.
3. Ajouter `GROQ_API_KEY` dans **Settings → Secrets** (optionnel).
4. Uploader un JSON dans la sidebar et lancer le pipeline.
