import os, json, anthropic

def reco_node(state):
    metrics  = state["metrics"]
    services = state["services"]
    anomalies = state["anomalies"]

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"recommendations": _rules(metrics, services)}

    try:
        client = anthropic.Anthropic(api_key=api_key)
        context = {
            "metrics_p95": {k: v["p95"] for k, v in metrics.items()},
            "metrics_max": {k: v["max"] for k, v in metrics.items()},
            "services_availability": {k: v["availability"] for k, v in services.items()},
            "critical_count": sum(1 for a in anomalies if a["severity"] == "critical"),
        }
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": (
                f"Infrastructure metrics over 10 days:\n{json.dumps(context, indent=2)}\n\n"
                "Return ONLY a valid JSON array of 5 recommendations. "
                "Each object: id, priority (Critique/Haute/Moyenne), category, title, observation, action, effort, impact."
            )}],
        )
        text = msg.content[0].text.strip().strip("```json").strip("```").strip()
        return {"recommendations": json.loads(text)}
    except Exception:
        return {"recommendations": _rules(metrics, services)}


def _rules(metrics, services):
    recos = []

    def add(priority, category, title, observation, action, effort, impact):
        recos.append({"id": f"R{len(recos)+1:02d}", "priority": priority, "category": category,
                      "title": title, "observation": observation, "action": action,
                      "effort": effort, "impact": impact})

    if metrics.get("cpu_usage", {}).get("p95", 0) > 80:
        add("Critique", "CPU", "Saturation CPU",
            f"p95={metrics['cpu_usage']['p95']}% max={metrics['cpu_usage']['max']}%",
            "Activer autoscaling horizontal. Auditer processus (htop). Load balancer actif/actif.",
            "2–4h", "−40% charge CPU")

    if metrics.get("memory_usage", {}).get("p95", 0) > 80:
        add("Critique", "Mémoire", "Pression mémoire",
            f"p95={metrics['memory_usage']['p95']}% max={metrics['memory_usage']['max']}%",
            "Analyser fuites mémoire. Ajuster limites JVM/Node. Optimiser TTL Redis.",
            "4–8h", "Stabilisation mémoire")

    if metrics.get("latency_ms", {}).get("p95", 0) > 250:
        add("Haute", "Latence", "Latence réseau élevée",
            f"p95={metrics['latency_ms']['p95']}ms max={metrics['latency_ms']['max']}ms",
            "Activer cache HTTP (Nginx). Vérifier keep-alive. Analyser slow query log.",
            "3–6h", "−50% latence P95")

    if metrics.get("disk_usage", {}).get("p95", 0) > 80:
        add("Critique", "Stockage", "Disque critique",
            f"p95={metrics['disk_usage']['p95']}% max={metrics['disk_usage']['max']}%",
            "Purger logs > 30j. Compresser backups. Alerte à 80%.",
            "1–2h", "+20Go libérés")

    if metrics.get("temperature_celsius", {}).get("p95", 0) > 75:
        add("Haute", "Matériel", "Surchauffe",
            f"p95={metrics['temperature_celsius']['p95']}°C",
            "Vérifier ventilation baie. Nettoyer filtres. Réduire densité.",
            "1j", "Prévention panne")

    for svc, stats in services.items():
        if stats["availability"] < 99:
            add("Critique" if stats["offline"] > 0 else "Haute", "Disponibilité",
                f"Indisponibilité {svc}",
                f"{svc} à {stats['availability']}% ({stats['offline']} offline)",
                f"Healthcheck + redémarrage auto (systemd). Failover secondaire.",
                "4–8h", f"SLA {svc} > 99.9%")

    return recos
