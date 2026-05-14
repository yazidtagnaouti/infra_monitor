from datetime import datetime, timezone
from collections import Counter

def report_node(state):
    records   = state["records"]
    anomalies = state["anomalies"]
    metrics   = state["metrics"]

    penalties  = max(0, metrics.get("cpu_usage",    {}).get("p95", 0) - 70) * 0.5
    penalties += max(0, metrics.get("memory_usage", {}).get("p95", 0) - 70) * 0.4
    penalties += max(0, metrics.get("disk_usage",   {}).get("p95", 0) - 70) * 0.3

    report = {
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "period":         {"start": records[0]["timestamp"], "end": records[-1]["timestamp"]},
        "total_records":  len(records),
        "health_score":   max(0, round(100 - penalties)),
        "metrics":        metrics,
        "services":       state["services"],
        "anomalies": {
            "total":    len(anomalies),
            "critical": sum(1 for a in anomalies if a["severity"] == "critical"),
            "warning":  sum(1 for a in anomalies if a["severity"] == "warning"),
            "by_metric": dict(Counter(a["metric"] for a in anomalies).most_common()),
        },
        "recommendations": state["recommendations"],
    }

    return {"report": report}
