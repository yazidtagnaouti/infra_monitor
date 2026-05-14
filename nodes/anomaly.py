"""
Nœud 3 — Détection d'anomalies : seuils configurables + état des services.
"""
from state import InfraState

THRESHOLDS = {
    "cpu_usage":           {"warn": 70,   "crit": 85},
    "memory_usage":        {"warn": 75,   "crit": 85},
    "latency_ms":          {"warn": 200,  "crit": 300},
    "disk_usage":          {"warn": 75,   "crit": 85},
    "error_rate":          {"warn": 0.03, "crit": 0.08},
    "temperature_celsius": {"warn": 70,   "crit": 80},
    "io_wait":             {"warn": 5,    "crit": 8},
}

LABELS = {
    "cpu_usage":           "CPU élevé",
    "memory_usage":        "Pression RAM",
    "latency_ms":          "Latence élevée",
    "disk_usage":          "Disque critique",
    "error_rate":          "Taux d'erreur",
    "temperature_celsius": "Surchauffe",
    "io_wait":             "I/O wait élevé",
}


def anomaly_node(state: InfraState) -> dict:
    records = state["records"]
    anomalies = []

    for r in records:
        ts = r["timestamp"]
        for metric, levels in THRESHOLDS.items():
            val = r.get(metric)
            if val is None:
                continue
            if val >= levels["crit"]:
                sev, thr = "critical", levels["crit"]
            elif val >= levels["warn"]:
                sev, thr = "warning", levels["warn"]
            else:
                continue
            anomalies.append({
                "timestamp": ts,
                "metric": metric,
                "value": val,
                "severity": sev,
                "threshold": thr,
                "message": f"{LABELS[metric]} : {val} (seuil {sev} = {thr})",
            })

        for svc, status in r.get("service_status", {}).items():
            if status in ("offline", "degraded"):
                anomalies.append({
                    "timestamp": ts,
                    "metric": f"service_{svc}",
                    "value": status,
                    "severity": "critical" if status == "offline" else "warning",
                    "threshold": "online",
                    "message": f"Service {svc} {status}",
                })

    return {"anomalies": anomalies}
