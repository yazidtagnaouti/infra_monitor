import os
from collections import Counter
import json
import re
from groq import Groq

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


def _parse_json_object(text: str):
    text = (text or "").strip()
    if "```" in text:
        for block in text.split("```"):
            block = block.strip()
            if block.lower().startswith("json"):
                block = block[4:].lstrip()
            if block.startswith("{"):
                text = block
                break
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        text = m.group(0)
    return json.loads(text)


def _anomaly_summary(anomalies):
    return {
        "total": len(anomalies),
        "by_metric": dict(Counter(a.get("metric", "") for a in anomalies).most_common(12)),
    }


def _with_detected_anomalies(preds, anomalies):
    preds["detected_anomalies"] = _anomaly_summary(anomalies)
    return preds


def _fallback_predictions(reason: str, anomalies=None):
    out = {
        "prediction_window_minutes": 60,
        "anomaly_predicted": False,
        "confidence": 0.0,
        "severity": "low",
        "predicted_anomalies": [],
        "overall_reasoning": reason,
        "recommended_actions": [],
        "source": "fallback",
    }
    if anomalies is not None:
        out["detected_anomalies"] = _anomaly_summary(anomalies)
    return out


def _normalize_predictions(raw):
    if not isinstance(raw, dict):
        return None
    required = (
        "prediction_window_minutes",
        "anomaly_predicted",
        "confidence",
        "severity",
        "predicted_anomalies",
        "overall_reasoning",
        "recommended_actions",
    )
    if not all(k in raw for k in required):
        return None
    predicted = raw.get("predicted_anomalies")
    if not isinstance(predicted, list):
        return None
    actions = raw.get("recommended_actions")
    if not isinstance(actions, list):
        return None
    return {
        "prediction_window_minutes": raw["prediction_window_minutes"],
        "anomaly_predicted": bool(raw["anomaly_predicted"]),
        "confidence": float(raw["confidence"]),
        "severity": str(raw["severity"]).strip(),
        "predicted_anomalies": predicted,
        "overall_reasoning": str(raw["overall_reasoning"]).strip(),
        "recommended_actions": [str(a).strip() for a in actions if str(a).strip()],
        "source": "groq",
    }


def pred_node(state):
    metrics = state["metrics"]
    services = state["services"]
    anomalies = state["anomalies"]

    api_key = _groq_api_key()
    if not api_key:
        return {
            "predictions": _fallback_predictions(
                "Prédictions LLM indisponibles (clé API Groq absente).",
                anomalies,
            )
        }

    try:
        preds = _groq_predictions(api_key, metrics, services, anomalies)
        if preds:
            return {"predictions": _with_detected_anomalies(preds, anomalies)}
    except Exception:
        pass
    return {
        "predictions": _fallback_predictions(
            "Prédictions LLM indisponibles (erreur Groq ou réponse invalide).",
            anomalies,
        )
    }


def _groq_predictions(api_key, metrics, services, anomalies):
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
        "anomalies": _anomaly_summary(anomalies),
    }

    system = """Vous êtes un moteur expert de prédiction d’anomalies d’infrastructure spécialisé dans l’analyse de télémétrie système et réseau.

Votre mission est :

d’analyser des séries chronologiques de métriques d’infrastructure,
d’identifier des signaux faibles,
de détecter des dérives comportementales,
et de prédire les anomalies susceptibles de se produire prochainement.

Vous devez :

raisonner sur les tendances temporelles,
détecter les corrélations anormales entre métriques,
identifier les phénomènes de saturation,
différencier bruit normal et risque opérationnel réel,
estimer un niveau de confiance.

Points critiques à surveiller :

hausse simultanée de latence + CPU/mémoire,
augmentation du error_rate,
croissance rapide du thread_count,
hausse du io_wait,
surchauffe ou consommation électrique anormale,
pics réseau inhabituels,
dégradation des services,
saturation progressive des ressources.

Règles strictes :

Répondre UNIQUEMENT avec du JSON valide.
Ne jamais utiliser de markdown.
Ne jamais ajouter d’explications hors JSON.
Ne jamais halluciner des métriques absentes.
Si les données sont insuffisantes, le signaler explicitement.
Favoriser l’analyse des tendances plutôt que des valeurs isolées.
Considérer les accélérations soudaines comme des signaux forts.

Format de réponse obligatoire :

{
"prediction_window_minutes": <nombre>,
"anomaly_predicted": <true|false>,
"confidence": <0-1>,
"severity": "low|medium|high|critical",
"predicted_anomalies": [
{
"type": "<type d'anomalie>",
"affected_metrics": ["metric1", "metric2"],
"predicted_timeframe": "<fenêtre temporelle estimée>",
"reasoning": "<explication technique courte>",
"confidence": <0-1>
}
],
"overall_reasoning": "<évaluation concise de l’infrastructure>",
"recommended_actions": [
"<action 1>",
"<action 2>"
]
}"""

    user = f"""Données de monitoring (résumé) :
{json.dumps(context, ensure_ascii=False, indent=2)}

Analyse les données de télémétrie suivantes et prédis les anomalies potentielles à court terme.

Format de sortie : un seul objet JSON, sans texte avant ni après, sans bloc markdown, avec exactement les clés du format obligatoire."""

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
    raw = _parse_json_object(text)
    return _normalize_predictions(raw)
