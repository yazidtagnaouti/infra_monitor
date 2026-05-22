from datetime import datetime, timezone
from collections import Counter

def report_node(state):
    records   = state["records"]
    anomalies = state["anomalies"]
    metrics   = state["metrics"]

    # rough heuristic, revisit
    cpu_p95 = metrics.get("cpu_usage", {}).get("p95", 0)
    mem_p95 = metrics.get("memory_usage", {}).get("p95", 0)
    disk_p95 = metrics.get("disk_usage", {}).get("p95", 0)

    penalties = 0
    penalties += max(0, cpu_p95 - 70) * 0.5
    penalties += max(0, mem_p95 - 70) * 0.4
    penalties += max(0, disk_p95 - 70) * 0.3

    analysis_summary = {
        **(state.get("analysis_summary") or {}),
        "recommendations": state.get("recommendations") or [],
    }

    report = {
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "period":           {"start": records[0]["timestamp"], "end": records[-1]["timestamp"]},
        "total_records":    len(records),
        "health_score":     max(0, round(100 - penalties)),
        "analysis_summary": analysis_summary,
        "metrics":          metrics,
        "services":         state["services"],
        "anomalies": {
            "total":    len(anomalies),
            "critical": sum(1 for a in anomalies if a["severity"] == "critical"),
            "warning":  sum(1 for a in anomalies if a["severity"] == "warning"),
            "by_metric": dict(Counter(a["metric"] for a in anomalies).most_common()),
        },
        "recommendations": state["recommendations"],
        "predictions": state.get("predictions") or {},
    }

    return {"report": report, "analysis_summary": analysis_summary}
