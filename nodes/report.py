"""
Nœud 5 — Rapport : assemble le JSON final + calcule le health score.
"""
from datetime import datetime, timezone
from collections import Counter
from state import InfraState


def report_node(state: InfraState) -> dict:
    records   = state["records"]
    anomalies = state["anomalies"]
    recos     = state["recommendations"]
    metrics   = state["metrics_summary"]

    critical = [a for a in anomalies if a["severity"] == "critical"]
    warnings  = [a for a in anomalies if a["severity"] == "warning"]

    # Health score (0–100)
    penalties  = max(0, metrics.get("cpu_usage",  {}).get("p95", 0) - 70) * 0.5
    penalties += max(0, metrics.get("memory_usage",{}).get("p95", 0) - 70) * 0.4
    penalties += max(0, metrics.get("disk_usage",  {}).get("p95", 0) - 70) * 0.3
    health_score = max(0, round(100 - penalties))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": ["ingestion_node", "analysis_node", "anomaly_node", "reco_node", "report_node"],
        "data_summary": {
            "total_records": len(records),
            "period_start": records[0]["timestamp"],
            "period_end":   records[-1]["timestamp"],
        },
        "health_score": health_score,
        "metrics_summary": metrics,
        "service_availability": state["service_availability"],
        "anomalies_summary": {
            "total":    len(anomalies),
            "critical": len(critical),
            "warning":  len(warnings),
            "by_metric": dict(Counter(a["metric"] for a in anomalies).most_common()),
        },
        "anomalies":       anomalies,
        "recommendations": recos,
    }

    return {"report": report}
