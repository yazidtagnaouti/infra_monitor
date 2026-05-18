from typing import TypedDict, List, Optional

class InfraState(TypedDict):
    records: List[dict]
    metrics: dict
    services: dict
    analysis_summary: Optional[dict]
    anomalies: List[dict]
    recommendations: List[dict]
    report: Optional[dict]
    errors: Optional[List[str]]  # started adding this, never wired up
