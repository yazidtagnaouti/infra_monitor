from collections import defaultdict

from nodes.anomaly import THRESHOLDS

METRICS = ['cpu_usage', 'memory_usage', 'latency_ms', 'disk_usage',
           'error_rate', 'temperature_celsius', 'io_wait']


def p95(vals):
    s = sorted(vals)
    return s[int(len(s) * 0.95)]


def _metric_status(p95, metric):
    levels = THRESHOLDS.get(metric)
    if not levels:
        return "ok"
    if p95 >= levels["crit"]:
        return "critical"
    if p95 >= levels["warn"]:
        return "warning"
    return "ok"


def _service_status(stats):
    if stats["offline"] > 0:
        return "critical"
    if stats["degraded"] > 0 or stats["availability"] < 99:
        return "warning"
    return "ok"


def make_summary(records, metrics, services):
    summary_metrics = {
        name: {**stats, "status": _metric_status(stats["p95"], name)}
        for name, stats in metrics.items()
    }
    summary_services = {
        name: {
            "availability_pct": stats["availability"],
            "online": stats["online"],
            "degraded": stats["degraded"],
            "offline": stats["offline"],
            "status": _service_status(stats),
        }
        for name, stats in services.items()
    }
    highlights = []
    for name, s in summary_metrics.items():
        if s["status"] != "ok":
            highlights.append(f"{name}: p95={s['p95']} ({s['status']})")
    for name, s in summary_services.items():
        if s["status"] != "ok":
            highlights.append(
                "{name}: {avail}% disponible ({off} offline, {deg} dégradé)".format(
                    name=name,
                    avail=s["availability_pct"],
                    off=s["offline"],
                    deg=s["degraded"],
                )
            )
    return {
        "period": {"start": records[0]["timestamp"], "end": records[-1]["timestamp"]},
        "records_count": len(records),
        "metrics": summary_metrics,
        "services": summary_services,
        "highlights": highlights,
    }


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
    # add more services here if needed
    for svc in ["database", "api_gateway", "cache"]:
        statuses = [r["service_status"][svc] for r in records if svc in r.get("service_status", {})]
        total = len(statuses)
        services[svc] = {
            "online": statuses.count("online"),
            "degraded": statuses.count("degraded"),
            "offline": statuses.count("offline"),
            "availability": round(statuses.count("online") / total * 100, 1),
        }

    analysis_summary = make_summary(records, metrics, services)
    return {"metrics": metrics, "services": services, "analysis_summary": analysis_summary}
