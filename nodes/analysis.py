"""
Nœud 2 — Analyse : statistiques descriptives + disponibilité services.
"""
from collections import defaultdict
from state import InfraState

NUMERIC_METRICS = [
    "cpu_usage", "memory_usage", "latency_ms", "disk_usage",
    "network_in_kbps", "network_out_kbps", "io_wait",
    "thread_count", "active_connections", "error_rate",
    "temperature_celsius", "power_consumption_watts",
]
SERVICES = ["database", "api_gateway", "cache"]


def _p95(values):
    s = sorted(values)
    return round(s[min(int(len(s) * 0.95), len(s) - 1)], 2)


def analysis_node(state: InfraState) -> dict:
    records = state["records"]
    buckets = defaultdict(list)
    for r in records:
        for m in NUMERIC_METRICS:
            if m in r:
                buckets[m].append(r[m])

    metrics_summary = {
        m: {
            "avg": round(sum(v) / len(v), 2),
            "min": round(min(v), 2),
            "max": round(max(v), 2),
            "p95": _p95(v),
        }
        for m, v in buckets.items()
    }

    service_availability = {}
    for svc in SERVICES:
        statuses = [r["service_status"].get(svc, "unknown") for r in records]
        total = len(statuses)
        online = statuses.count("online")
        service_availability[svc] = {
            "online": online,
            "degraded": statuses.count("degraded"),
            "offline": statuses.count("offline"),
            "availability_pct": round(online / total * 100, 1),
        }

    return {"metrics_summary": metrics_summary, "service_availability": service_availability}
