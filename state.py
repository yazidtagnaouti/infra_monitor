from typing import TypedDict, List, Optional

class InfraState(TypedDict):
    records: List[dict]
    metrics: dict
    services: dict
    anomalies: List[dict]
    recommendations: List[dict]
    report: Optional[dict]
