import json, os

def ingestion_node(state):
    path = state.get("source", os.path.join(os.path.dirname(__file__), '../data.json'))
    with open(path) as f:
        records = json.load(f)
    # TODO: handle empty records edge case
    return {"records": records}
