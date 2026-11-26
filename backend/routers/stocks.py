"""GET /api/stocks/{ticker} et POST /api/market/refresh (EF-03, RG-03, ENF-02, UI §4.5, §5.4).

En bref :

**Fiche action** : un seul appel alimente les deux onglets (Graphique et Infos sur
l'action). On renvoie l'en-tête (cours, conseil, note), un an de cours avec les
indicateurs (moyennes mobiles, Bollinger, RSI, MACD) calculés à partir de tout
l'historique, le conseil et ses raisons, la prévision en % et en euros, le dividende,
les actualités des 7 derniers jours, les ratios des deux derniers exercices et le poids
de chaque pilier.

**Actualisation** : relance la collecte et le recalcul des conseils, en arrière-plan.
Le bouton est public : une actualisation toutes les 2 minutes au plus (code 429 sinon).
"""

from __future__ import annotations

import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response

import config
from routers.dashboard import stock_row
from routers.deps import check_ticker, get_collector, get_now, get_repo, money
from services import market_data
from services.decision_engine import forecast_euros
from services.info_scoring import article_weight
from services.portfolio_service import MENTION, load_state
from services.ratio_scoring import estimated_dividend, growth_pct
from services.refresh_service import refresh
from services.technical_scoring import compute_indicators

router = APIRouter(prefix="/api", tags=["actions"])

CHART_DAYS = 365
SERIES = ("open", "high", "low", "close", "mm20", "mm50", "mm200", "boll_haut", "boll_milieu", "boll_bas",
          "rsi", "macd", "macd_signal", "macd_hist")
PILIERS = (("infos", "Informations"), ("tech", "Analyse graphique"), ("ratios", "Ratios"), ("hasard", "Hasard"))


def _num(value: Any, digits: int = 4) -> float | None:
    if value is None:
        return None
    value = float(value)
    return None if math.isnan(value) else round(value, digits)


def _age_label(days: float) -> str:
    if days < 1:
        hours = max(1, int(days * 24))
        return f"Il y a {hours} heure{'s' if hours > 1 else ''}"
    whole = int(days)
    return f"Il y a {whole} jour{'s' if whole > 1 else ''}"


def rsi_zone(rsi: float | None) -> str | None:
    if rsi is None:
        return None
    if rsi <= 30:
        return "titre survendu (forte baisse récente)"
    if rsi >= 70:
        return "titre suracheté (forte hausse récente)"
    return "zone neutre"


def macd_label(signal: float | None) -> str | None:
    return {
        1.0: "Croisement haussier cette semaine",
        -1.0: "Croisement baissier cette semaine",
        0.5: "Dynamique haussière",
        -0.5: "Dynamique baissière",
    }.get(signal)


@router.get("/stocks/{ticker}")
def stock_detail(ticker: str, repo=Depends(get_repo), now: datetime = Depends(get_now)) -> dict[str, Any]:
    state = load_state(repo)
    action = check_ticker(ticker, state.actions)
    ticker = action["ticker"]
    score = state.scores.get(ticker) or {}
    details = score.get("details_piliers", {})
    row = stock_row(ticker, state)
    held = state.held.get(ticker, 0)
    position_value = Decimal(held) * state.prices[ticker]

    with ThreadPoolExecutor(max_workers=3) as pool:
        history_job = pool.submit(repo.get_history, action["id"])
        articles_job = pool.submit(repo.get_articles, action["id"], now - timedelta(days=config.INFO_FENETRE_JOURS))
        ratios_job = pool.submit(repo.get_ratios, action["id"])
        history, articles, all_ratios = history_job.result(), articles_job.result(), ratios_job.result()
    chart = []
    if not history.empty:
        indicators = compute_indicators(history)
        recent = indicators[indicators["date_seance"] >= now.date() - timedelta(days=CHART_DAYS)]
        chart = [
            {"date": r["date_seance"].isoformat(), **{k: _num(r[k]) for k in SERIES}}
            for r in recent.to_dict("records")
        ]
    tech = details.get("tech", {})
    rsi = (tech.get("details") or {}).get("rsi")

    news = []
    for article in articles:
        if not market_data.is_relevant(ticker, article["titre"], article.get("resume")):
            continue
        age = (now - article["date_pub"]).total_seconds() / 86400
        weight = article_weight(age)
        if weight <= 0:
            continue
        text = f"{article['titre']} {article.get('resume') or ''}"
        news.append(
            {
                "titre": article["titre"],
                "resume": article.get("resume"),
                "source": article.get("source"),
                "url": article.get("url"),
                "date_pub": article["date_pub"].isoformat(),
                "age": _age_label(age),
                "type": "Annonce officielle" if market_data.is_announcement(text) else "Actualité",
                "score_impact": _num(article["score_impact"], 1),
                "poids": round(weight, 3),
            }
        )
    news.sort(key=lambda a: a["poids"], reverse=True)

    ratios = all_ratios[:2]
    exercices = [
        {
            "annee": int(r["date_maj"][:4]),
            "chiffre_affaires": _num(r.get("chiffre_affaires"), 0),
            "dividende_par_action": _num(r.get("dividende_par_action"), 2),
            "rendement_pct": _num(r.get("rendement_pct"), 2),
        }
        for r in reversed(ratios)
    ]
    evolution = {}
    if len(exercices) == 2:
        old, new = exercices
        evolution = {
            "chiffre_affaires_pct": _num(growth_pct(new["chiffre_affaires"], old["chiffre_affaires"]), 1),
            "dividende_par_action_pct": _num(growth_pct(new["dividende_par_action"], old["dividende_par_action"]), 1),
        }
    ratio_details = details.get("ratios", {})
    prevision = details.get("prevision")
    scenarios = None if not prevision else {k: prevision[k] for k in ("defavorable", "central", "favorable")}
    infos = details.get("infos", {})

    return {
        "entete": {
            **{k: row[k] for k in ("ticker", "nom", "secteur", "cours", "variation_jour_pct", "conseil", "note",
                                   "confiance", "detenues", "valeur_position")},
            "place": "Euronext Paris",
            "date_donnees": action.get("maj_le"),
            "date_calcul": score.get("date_calcul"),
        },
        "graphique": {
            "series": chart,
            "rsi": {"valeur": _num(rsi, 0), "zone": rsi_zone(rsi)},
            "macd": {"libelle": macd_label((tech.get("signaux") or {}).get("macd"))},
        },
        "conseil": {
            "decision": row["conseil"],
            "note": row["note"],
            "confiance": row["confiance"],
            "seuil_achat": config.SEUIL_ACHAT,
            "seuil_vente": config.SEUIL_VENTE,
            "raisons": row["raisons"],
        },
        "prevision": {
            "pct": scenarios,
            "eur": forecast_euros(scenarios, position_value) if held else None,
            "valeur_position": money(position_value),
            "disponible": scenarios is not None,
        },
        "dividende": {
            "par_action": money(action.get("dividende_estime")),
            "detenues": held,
            "estime_eur": money(estimated_dividend(held, action.get("dividende_estime"))),
        },
        "infos": {
            "note": _num(infos.get("score"), 1),
            "impact_points": _num(infos.get("impact_points"), 1),
            "message": infos.get("message"),
            "actualites": news,
            "ratios": {
                "note": _num(ratio_details.get("score"), 1),
                "exercices": exercices,
                "evolution": evolution,
                "rendement_actuel_pct": _num(ratio_details.get("rendement_pct"), 2),
                "moyenne_rendement_5_pct": _num(ratio_details.get("moyenne_rendement_pct"), 2),
            },
            "piliers": [
                {"cle": key, "nom": label, "poids": config.POIDS[key], "note": _num(details.get(key, {}).get("score"), 1)}
                for key, label in PILIERS
            ],
        },
        "mention": MENTION,
    }


# ---------------------------------------------------------------------------
# Actualisation (ENF-02, D-11)
# ---------------------------------------------------------------------------
# Le bouton rend la main tout de suite (202) : la collecte continue en arrière-plan et
# l'interface demande où elle en est (GET /api/market/refresh/status). ?attendre=true
# fait tout d'un coup (tâche planifiée GitHub, tests).

_refresh_lock = threading.Lock()
_refresh = {"en_cours": False, "lance_le": None, "termine_le": None, "rapport": None, "erreur": None}
_last_refresh = {"at": 0.0}
_last_newsapi = {"at": 0.0}


def _news_key() -> str:
    """Clé NewsAPI seulement si le dernier appel date de plus de 15 minutes (quota gratuit)."""
    key = config.load_settings().news_api_key
    now = time.monotonic()
    if key and (not _last_newsapi["at"] or now - _last_newsapi["at"] >= config.NEWSAPI_INTERVALLE_MIN_SECONDES):
        _last_newsapi["at"] = now
        return key
    return ""


def _run_refresh(repo, collector) -> None:
    try:
        _refresh["rapport"] = refresh(repo, collector, news_api_key=_news_key())
        _refresh["erreur"] = None
    except Exception as error:  # l'erreur est montrée à l'interface, la clé n'y figure jamais
        _refresh["erreur"] = f"{type(error).__name__}: {error}"
    finally:
        if hasattr(repo, "invalidate"):
            repo.invalidate()  # les écrans relisent les nouvelles données
        _refresh["en_cours"] = False
        _refresh["termine_le"] = datetime.now(timezone.utc).isoformat(timespec="seconds")


@router.post("/market/refresh", status_code=202)
def market_refresh(
    background: BackgroundTasks,
    response: Response,
    attendre: bool = False,
    repo=Depends(get_repo),
    collector=Depends(get_collector),
) -> dict[str, Any]:
    with _refresh_lock:
        if _refresh["en_cours"]:
            return {"statut": "en_cours", "lance_le": _refresh["lance_le"]}
        wait = config.REFRESH_INTERVALLE_MIN_SECONDES - (time.monotonic() - _last_refresh["at"])
        if _last_refresh["at"] and wait > 0:
            raise HTTPException(
                status_code=429,
                detail=f"Données actualisées il y a moins de 2 minutes : réessayez dans {math.ceil(wait)} s.",
                headers={"Retry-After": str(math.ceil(wait))},
            )
        _last_refresh["at"] = time.monotonic()
        _refresh.update(en_cours=True, lance_le=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        termine_le=None, erreur=None)
    if attendre:
        _run_refresh(repo, collector)
        response.status_code = 500 if _refresh["erreur"] else 200
        return {"statut": "erreur" if _refresh["erreur"] else "termine", "erreur": _refresh["erreur"],
                **(_refresh["rapport"] or {})}
    background.add_task(_run_refresh, repo, collector)
    return {"statut": "lance", "lance_le": _refresh["lance_le"]}


@router.get("/market/refresh/status")
def market_refresh_status() -> dict[str, Any]:
    """Où en est l'actualisation : en cours, terminée (avec son compte rendu) ou en erreur."""
    return dict(_refresh)
