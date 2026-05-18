import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from langgraph.graph import StateGraph, END
from state import InfraState
from nodes.ingestion import ingestion_node
from nodes.analysis  import analysis_node
from nodes.anomaly   import anomaly_node
from nodes.reco      import reco_node
from nodes.report    import report_node

def build_pipeline():
    g = StateGraph(InfraState)
    g.add_node("ingestion", ingestion_node)
    g.add_node("analysis",  analysis_node)
    g.add_node("anomaly_detection", anomaly_node)  # FIXME rename file someday
    g.add_node("reco",      reco_node)
    g.add_node("report",    report_node)
    g.set_entry_point("ingestion")
    g.add_edge("ingestion", "analysis")
    g.add_edge("analysis",  "anomaly_detection")
    g.add_edge("anomaly_detection", "reco")
    g.add_edge("reco",      "report")
    g.add_edge("report",    END)
    # print(g.get_graph().draw_ascii())  # was debugging flow order
    return g.compile()
