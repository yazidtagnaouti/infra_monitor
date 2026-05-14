from collections import defaultdict

METRICS = ["cpu_usage", "memory_usage", "latency_ms", "disk_usage",
           "error_rate", "temperature_celsius", "io_wait"]

def p95(vals):
    s = sorted(vals)
    return s[int(len(s) * 0.95)]

def analysis_node(state):
    records = state["records"]
    buckets = defaultdict(list)
    for r in records:
        for m in METRICS:
            if m in r:
                buckets[m].append(r[m])

    metrics = {
        m: {"avg": round(sum(v)/len(v), 2), "min": min(v), "max": max(v), "p95": p95(v)}
        for m, v in buckets.items()
    }

    services = {}
    for svc in ["database", "api_gateway", "cache"]:
        statuses = [r["service_status"][svc] for r in records if svc in r.get("service_status", {})]
        total = len(statuses)
        services[svc] = {
            "online": statuses.count("online"),
            "degraded": statuses.count("degraded"),
            "offline": statuses.count("offline"),
            "availability": round(statuses.count("online") / total * 100, 1),
        }

    return {"metrics": metrics, "services": services}
