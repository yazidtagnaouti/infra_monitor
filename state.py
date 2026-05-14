"""
state.py — État partagé entre tous les nœuds LangGraph.
"""
from typing import TypedDict, List, Optional


class Anomaly(TypedDict):
    timestamp: str
    metric: str
    value: float | str
    severity: str        # "critical" | "warning"
    threshold: float | str
    message: str


class Recommendation(TypedDict):
    id: str
    priority: str
    category: str
    title: str
    observation: str
    action: str
    effort: str
    impact: str


class InfraState(TypedDict):
    records: List[dict]
    metrics_summary: dict
    service_availability: dict
    anomalies: List[Anomaly]
    recommendations: List[Recommendation]
    report: Optional[dict]
