"""
Nœud 4 — Recommandations via Claude API (Anthropic free tier).

Modèle : claude-haiku-4-5-20251001
Free tier : https://console.anthropic.com
Fallback  : règles Python pures si pas de clé API.
"""

import os
import json
from collections import Counter
from state import InfraState


def _rule_based_recos(summary, svc, anomalies):
    recos = []

    def add(priority, category, title, observation, action, effort, impact):
        rid = f"R{len(recos)+1:02d}"
        recos.append(dict(id=rid, priority=priority, category=category,
                          title=title, observation=observation,
                          action=action, effort=effort, impact=impact))

    cpu = summary.get("cpu_usage", {})
    if cpu.get("p95", 0) > 80:
        add("Critique", "CPU", "Saturation CPU récurrente",
            f"CPU p95={cpu['p95']}%, max={cpu['max']}%",
            "1. Activer l'autoscaling horizontal (AWS ASG / K8s HPA). "
            "2. Auditer les processus consommateurs (htop, py-spy). "
            "3. Déployer un load balancer actif/actif.",
            "2–4h", "−40% charge CPU estimée")

    mem = summary.get("memory_usage", {})
    if mem.get("p95", 0) > 80:
        add("Critique", "Mémoire", "Pression mémoire — risque de swap",
            f"RAM p95={mem['p95']}%, max={mem['max']}%",
            "1. Analyser les fuites mémoire (memory_profiler). "
            "2. Ajuster limites JVM ou Node.js. "
            "3. Optimiser la politique d'éviction Redis (allkeys-lru).",
            "4–8h", "Stabilisation mémoire")

    lat = summary.get("latency_ms", {})
    if lat.get("p95", 0) > 250:
        add("Haute", "Latence", "Pics de latence réseau",
            f"Latence p95={lat['p95']}ms, max={lat['max']}ms",
            "1. Activer le cache HTTP (Nginx/Varnish). "
            "2. Vérifier keep-alive sur les connexions HTTP. "
            "3. Analyser les requêtes lentes via slow query log.",
            "3–6h", "−50% latence P95")

    disk = summary.get("disk_usage", {})
    if disk.get("p95", 0) > 80:
        add("Critique", "Stockage", "Espace disque critique",
            f"Disque p95={disk['p95']}%, max={disk['max']}%",
            "1. Purger les logs > 30 jours (logrotate). "
            "2. Compresser les backups WAL. "
            "3. Alerte automatique à 80%.",
            "1–2h", "+20 Go libérés")

    temp = summary.get("temperature_celsius", {})
    if temp.get("p95", 0) > 75:
        add("Haute", "Matériel", "Surchauffe serveur",
            f"Température p95={temp['p95']}°C, max={temp['max']}°C",
            "1. Vérifier ventilation baie. "
            "2. Nettoyer filtres à poussière. "
            "3. Réduire densité de charge.",
            "1 journée", "Prévention panne matérielle")

    err = summary.get("error_rate", {})
    if err.get("p95", 0) > 0.05:
        add("Haute", "Fiabilité", "Taux d'erreur anormal",
            f"Error rate p95={err['p95']}, max={err['max']}",
            "1. Analyser les logs d'erreur (Kibana/Loki). "
            "2. Implémenter un circuit breaker. "
            "3. Ajouter retry avec backoff exponentiel.",
            "1–2 jours", "Taux d'erreur < 1%")

    for service, stats in svc.items():
        if stats["availability_pct"] < 99:
            sev = "Critique" if stats["offline"] > 0 else "Haute"
            add(sev, "Disponibilité", f"Disponibilité insuffisante — {service}",
                f"{service} à {stats['availability_pct']}% "
                f"({stats['offline']} offline, {stats['degraded']} dégradés)",
                f"1. Healthcheck automatique sur {service}. "
                f"2. Redémarrage auto (systemd Restart=always). "
                f"3. Failover sur nœud secondaire.",
                "4–8h", f"SLA {service} > 99.9%")

    return recos


def _claude_recos(summary, svc, anomalies, api_key):
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    top_anomalies = Counter(
        a["metric"] for a in anomalies if a["severity"] == "critical"
    ).most_common(7)

    context = {
        "metrics_p95": {k: v["p95"] for k, v in summary.items()},
        "metrics_max": {k: v["max"] for k, v in summary.items()},
        "metrics_avg": {k: v["avg"] for k, v in summary.items()},
        "service_availability_pct": {k: v["availability_pct"] for k, v in svc.items()},
        "service_incidents": {
            k: {"offline": v["offline"], "degraded": v["degraded"]}
            for k, v in svc.items()
        },
        "top_critical_metrics": [
            {"metric": m, "critical_events": c} for m, c in top_anomalies
        ],
    }

    prompt = f"""Tu es un expert en infrastructure système pour une PME française.
Analyse ces métriques de monitoring collectées sur 10 jours et génère des recommandations.

DONNÉES :
{json.dumps(context, indent=2, ensure_ascii=False)}

Génère exactement 6 recommandations. Réponds UNIQUEMENT avec un tableau JSON valide, sans texte ni markdown.
Chaque objet doit avoir : id (R01...), priority (Critique/Haute/Moyenne), category, title (<60 chars), observation, action (étapes numérotées), effort, impact.
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def reco_node(state: InfraState) -> dict:
    summary   = state["metrics_summary"]
    svc       = state["service_availability"]
    anomalies = state["anomalies"]

    # Priorité : st.secrets (Streamlit Cloud) > variable d'environnement
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if api_key:
        try:
            recos = _claude_recos(summary, svc, anomalies, api_key)
            print("[Nœud 4] ✓ Claude Haiku — recommandations générées")
        except Exception as e:
            print(f"[Nœud 4] ⚠ Erreur Claude ({e}) → fallback règles Python")
            recos = _rule_based_recos(summary, svc, anomalies)
    else:
        print("[Nœud 4] ℹ Pas de clé API → règles Python pures")
        recos = _rule_based_recos(summary, svc, anomalies)

    return {"recommendations": recos}
