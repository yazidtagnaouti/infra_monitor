import json
import os
import re
from collections import Counter
from groq import Groq

# Partie 2 – Améliorations (30 minutes)
# Nœud d’Analyse Prédictive 
# Objectif : Exploiter l’historique des données pour identifier les tendances émergentes, 
# anticiper les défaillances et les surcharges potentielles, et ainsi optimiser la planification des ressources.


def _groq_api_key():
    key = os.getenv("GROQ_API_KEY", "").strip()
    if key:
        return key
    try:
        from config import GROQ_API_KEY

        return str(GROQ_API_KEY or "").strip()
    except ImportError:
        return ""


def _groq_model():
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()


def _parse_json_array(text: str):
    text = (text or "").strip()
    if "```" in text:
        for block in text.split("```"):
            block = block.strip()
            if block.lower().startswith("json"):
                block = block[4:].lstrip()
            if block.startswith("["):
                text = block
                break
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        text = m.group(0)
    return json.loads(text)


def _normalize_recommendations(raw):
    # expects 3-8 items with all keys filled
    if not isinstance(raw, list):
        return None
    required = ("id", "priority", "category", "title", "observation", "action", "effort", "impact")
    out = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        if not all(k in item and str(item[k]).strip() for k in required):
            continue
        rid = str(item["id"]).strip() or "R{:02d}".format(i + 1)
        out.append(
            {
                "id": rid[:8],
                "priority": str(item["priority"]).strip(),
                "category": str(item["category"]).strip(),
                "title": str(item["title"]).strip()[:120],
                "observation": str(item["observation"]).strip(),
                "action": str(item["action"]).strip(),
                "effort": str(item["effort"]).strip(),
                "impact": str(item["impact"]).strip(),
            }
        )
        if len(out) >= 8:
            break
    if len(out) < 3:
        return None
    return out[:8]


def reco_node(state):
    metrics = state["metrics"]
    services = state["services"]
    anomalies = state["anomalies"]
    # TODO: maybe cache this when same metrics hash

    api_key = _groq_api_key()
    if not api_key:
        return {"recommendations": _rules(metrics, services)}

    try:
        recos = _groq_recommendations(api_key, metrics, services, anomalies)
        if recos:
            return {"recommendations": recos}
    except Exception:
        pass
    return {"recommendations": _rules(metrics, services)}


def _groq_recommendations(api_key, metrics, services, anomalies):
    critical = [a for a in anomalies if a.get("severity") == "critical"]
    warning = [a for a in anomalies if a.get("severity") == "warning"]
    top_metrics = dict(Counter(a.get("metric", "") for a in anomalies).most_common(12))

    context = {
        "metrics_p95": {k: round(v.get("p95", 0), 4) for k, v in metrics.items()},
        "metrics_max": {k: round(v.get("max", 0), 4) for k, v in metrics.items()},
        "metrics_avg": {k: round(v.get("avg", 0), 4) for k, v in metrics.items()},
        "services": {
            name: {
                "availability_pct": s.get("availability"),
                "online": s.get("online"),
                "degraded": s.get("degraded"),
                "offline": s.get("offline"),
            }
            for name, s in services.items()
        },
        "anomalies": {
            "total": len(anomalies),
            "critical_count": len(critical),
            "warning_count": len(warning),
            "by_metric": top_metrics,
        },
        "recent_critical_samples": critical[:12],
    }

    system = """Tu rédiges des recommandations d'exploitation pour des ingénieurs qui lisent un rapport interne.
Style : ton direct, phrases courtes. Pas d'emojis. Pas d'introduction du type "Dans le cadre de…", "Il est essentiel de…", "En tant qu'expert…". Pas de listes numérotées 1. 2. 3. dans les champs texte.
Les titres doivent ressembler à des titres d'actions Jira ou de tickets d'astreinte, pas à du marketing.
Les observations doivent s'appuyer sur des chiffres ou faits présents dans les données fournies (cite les valeurs quand c'est pertinent).
Le champ action : 2 ou 3 formulations impératives courtes, séparées par des points-virgules ; pas de markdown."""

    user = f"""Données de monitoring (résumé) :
{json.dumps(context, ensure_ascii=False, indent=2)}

Tâche : produire exactement 5 recommandations, triées de la plus urgente à la moins urgente, en t'appuyant uniquement sur ce qui apparaît dans les données (métriques, services, anomalies). Ne invente pas d'incidents absents des chiffres — basically stick to what's in the json.

Format de sortie : un seul tableau JSON (array), sans texte avant ni après, sans bloc markdown.
Chaque élément du tableau doit avoir exactement ces clés : "id" (ex. R01), "priority" (une seule valeur parmi : Critique, Haute, Moyenne), "category", "title" (max 70 caractères), "observation", "action", "effort", "impact".
effort : estimation réaliste du type "2 h", "1 j", "3–5 j".
impact : une phrase courte orientée résultat opérationnel, sans superlatifs ni promesse vague."""

    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model=_groq_model(),
        max_tokens=2048,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = completion.choices[0].message.content or ""
    raw = _parse_json_array(text)
    return _normalize_recommendations(raw)


def _rules(metrics, services):
    if not metrics:
        return []

    recos = []

    def add(priority, category, title, observation, action, effort, impact):
        recos.append(
            {
                "id": f"R{len(recos) + 1:02d}",
                "priority": priority,
                "category": category,
                "title": title,
                "observation": observation,
                "action": action,
                "effort": effort,
                "impact": impact,
            }
        )

    if metrics.get("cpu_usage", {}).get("p95", 0) > 80:
        add(
            "Critique",
            "CPU",
            "Saturation CPU",
            f"p95={metrics['cpu_usage']['p95']}% max={metrics['cpu_usage']['max']}%",
            "Activer autoscaling horizontal ; auditer processus (htop) ; load balancer actif/actif.",
            "2–4 h",
            "Réduction sensible de la charge CPU sur les pics.",
        )

    if metrics.get("memory_usage", {}).get("p95", 0) > 80:
        add("Critique", "Mémoire", "Pression mémoire",
            "p95={}% max={}%".format(metrics['memory_usage']['p95'], metrics['memory_usage']['max']),
            "Analyser fuites mémoire ; ajuster limites JVM/Node ; revoir TTL Redis.",
            "4–8 h", "Stabilisation mémoire et risque de swap réduit.")

    if metrics.get("latency_ms", {}).get("p95", 0) > 250:
        add(
            "Haute",
            "Latence",
            "Latence réseau élevée",
            f"p95={metrics['latency_ms']['p95']} ms max={metrics['latency_ms']['max']} ms",
            "Mettre en cache HTTP (Nginx) ; vérifier keep-alive ; analyser slow query log.",
            "3–6 h",
            "Baisse attendue sur la latence p95.",
        )

    if metrics.get("disk_usage", {}).get("p95", 0) > 80:
        recos.append({
            "id": "R{:02d}".format(len(recos) + 1),
            "priority": "Critique",
            "category": "Stockage",
            "title": "Disque critique",
            "observation": f"p95={metrics['disk_usage']['p95']}% max={metrics['disk_usage']['max']}%",
            "action": "Purger les logs anciennes ; compresser les backups ; alerte disque à 80 %.",
            "effort": "1–2 h",
            "impact": "Espace disque récupéré rapidement.",
        })

    if metrics.get("temperature_celsius", {}).get("p95", 0) > 75:
        add(
            "Haute",
            "Matériel",
            "Surchauffe",
            f"p95={metrics['temperature_celsius']['p95']} °C",
            "Contrôler ventilation baie ; nettoyer filtres ; réduire densité de charge.",
            "1 j",
            "Risque panne thermique diminué.",
        )

    for svc, stats in services.items():
        if stats["availability"] < 99:
            prio = "Critique" if stats["offline"] > 0 else "Haute"
            add(
                prio,
                "Disponibilité",
                f"Indisponibilité {svc}",
                f"{svc} à {stats['availability']}% ({stats['offline']} offline)",
                "Healthcheck systématique ; redémarrage auto (systemd) ; prévoir failover.",
                "4–8 h",
                f"Remonter la dispo {svc} vers l'objectif SLA.",
            )

    return recos
