"""
Nœud 1 — Ingestion : lit et valide le fichier JSON d'entrée.
Accepte un chemin de fichier ou une liste déjà chargée (pour Streamlit upload).
"""
import json
from state import InfraState

REQUIRED_FIELDS = {
    "timestamp", "cpu_usage", "memory_usage", "latency_ms",
    "disk_usage", "error_rate", "temperature_celsius",
    "io_wait", "active_connections", "service_status",
}


def ingestion_node(state: InfraState) -> dict:
    # Si les records sont déjà injectés (depuis Streamlit), on les utilise
    if state.get("records"):
        records = state["records"]
    else:
        import os
        path = os.path.join(os.path.dirname(__file__), "..", "data.json")
        with open(os.path.abspath(path), encoding="utf-8") as f:
            raw = json.load(f)
        records = [r for r in raw if not (REQUIRED_FIELDS - set(r.keys()))]

    return {"records": records}
