THRESHOLDS = {
    "cpu_usage":           {"warn": 70,   "crit": 85},
    "memory_usage":        {"warn": 75,   "crit": 85},
    "latency_ms":          {"warn": 200,  "crit": 300},
    "disk_usage":          {"warn": 75,   "crit": 85},
    "error_rate":          {"warn": 0.03, "crit": 0.08},
    "temperature_celsius": {"warn": 70,   "crit": 80},
    "io_wait":             {"warn": 5,    "crit": 8},
}

def anomaly_node(state):
    anomalies = []
    for r in state["records"]:
        for metric, levels in THRESHOLDS.items():
            val = r.get(metric)
            if val is None:
                continue
            if val >= levels["crit"]:
                anomalies.append({"ts": r["timestamp"], "metric": metric, "value": val, "severity": "critical"})
            elif val >= levels["warn"]:
                anomalies.append({"ts": r["timestamp"], "metric": metric, "value": val, "severity": "warning"})

        for svc, status in r.get("service_status", {}).items():
            if status != "online":
                sev = "critical" if status == "offline" else "warning"
                anomalies.append({"ts": r["timestamp"], "metric": f"service_{svc}", "value": status, "severity": sev})

    return {"anomalies": anomalies}
