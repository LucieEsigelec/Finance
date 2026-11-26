"""Actualisation des données et recalcul des conseils — POST /api/market/refresh (ENF-02).

En bref, pour chacune des 5 actions :
1. **collecter** : nouveaux cours (yfinance), ratios des deux derniers exercices,
   actualités des 7 derniers jours (Google News, NewsAPI) ; on n'ajoute que ce qui
   manque en base ;
2. **calculer** les 4 notes, la note finale, le conseil, les raisons et la prévision ;
3. **enregistrer** une nouvelle ligne dans ``scores_actions`` et mettre à jour le
   dernier cours et le dividende attendu dans ``actions``.

Enfin, le lundi, on **ouvre la semaine** : la valeur du portefeuille au dernier cours
de la semaine précédente devient la référence de l'alerte de perte (SPEC §11.1).

Une source en panne n'arrête pas l'actualisation : l'erreur est notée dans le compte
rendu et les données déjà en base sont utilisées.
"""

from __future__ import annotations

import logging
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from statistics import mean
from typing import Any, Mapping

import pandas as pd

import config
from services import market_data
from services.common import round_half_up
from services.decision_engine import (
    ACHAT,
    build_reasons,
    confidence,
    decide,
    final_score,
    forecast,
    weekly_returns,
)
from services.info_scoring import InfoScoringService
from services.randomness_service import RandomnessService
from services.ratio_scoring import RatioScoringService
from services.technical_scoring import TechnicalScoringService

log = logging.getLogger(__name__)


class MarketCollector:
    """Les trois collectes externes, regroupées pour pouvoir les remplacer dans les tests."""

    def history(self, ticker: str, since: date | None) -> list[dict[str, Any]]:
        return market_data.fetch_history(ticker, since)

    def fundamentals(self, ticker: str, history: pd.DataFrame, today: date) -> market_data.Fundamentals:
        return market_data.fetch_fundamentals(ticker, history, today)

    def news(self, ticker: str, now: datetime, api_key: str) -> tuple[list[dict[str, Any]], list[str]]:
        return market_data.fetch_news(ticker, now, api_key)

    def intraday(self, ticker: str, period: str | None = None) -> list[dict[str, Any]]:
        return market_data.fetch_intraday(ticker, period)


def json_safe(value: Any) -> Any:
    """Remplace NaN / infini par None et les nombres numpy par des nombres Python :
    Postgres refuse NaN dans une colonne JSONB."""
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else float(value)
    if hasattr(value, "item"):  # nombre numpy
        return json_safe(value.item())
    return value


def current_yield(dividend: Decimal | None, price: float | None) -> float | None:
    if not dividend or not price:
        return None
    return float(dividend) / price * 100


def _num(value: Any) -> float | None:
    return None if value is None else float(value)


def score_stock(
    ticker: str,
    history: pd.DataFrame,
    ratios: list[Mapping[str, Any]],
    articles: list[Mapping[str, Any]],
    rendement: float | None,
    moyenne_rendement: float | None,
    dividende_par_action: Decimal | None,
    now: datetime,
) -> dict[str, Any]:
    """Toutes les notes d'un titre et le détail enregistré dans details_piliers (SPEC A.1)."""
    today = now.date()
    tech = TechnicalScoringService().score(history, today)
    info = InfoScoringService().score(articles, now)
    latest = ratios[0] if ratios else {}
    previous = ratios[1] if len(ratios) > 1 else {}
    ratio = RatioScoringService().score(
        _num(latest.get("chiffre_affaires")),
        _num(previous.get("chiffre_affaires")),
        _num(latest.get("dividende_par_action")),
        _num(previous.get("dividende_par_action")),
        rendement,
        moyenne_rendement,
    )
    hasard = RandomnessService().score(ticker, today)

    notes = {"infos": info.score, "tech": tech.score, "ratios": ratio.score, "hasard": hasard.score}
    note = final_score(notes)
    conseil = decide(note)
    past = history[pd.to_datetime(history["date_seance"]).dt.date <= today] if not history.empty else history
    prevision = forecast(weekly_returns(past), note) if not past.empty else None
    raisons = build_reasons(
        note, conseil, notes, tech.signaux, info.faits_cles, ratio, info_message=info.message
    )
    details = {
        "infos": {
            "score": round(info.score, 2),
            "faits_cles": [f["titre"] for f in info.faits_cles],
            "faits": info.faits_cles,
            "nb_articles": info.nb_articles,
            "message": info.message,
            "impact_points": round(info.impact_points, 2),
        },
        "tech": {"score": round(tech.score, 2), "signaux": tech.signaux, "details": tech.details},
        "ratios": {
            "score": round(ratio.score, 2),
            "criteres": ratio.criteres,
            "croissance_ca_pct": ratio.croissance_ca_pct,
            "croissance_dpa_pct": ratio.croissance_dpa_pct,
            "rendement_pct": ratio.rendement_pct,
            "moyenne_rendement_pct": ratio.moyenne_rendement_pct,
        },
        "hasard": {"score": round(hasard.score, 2), "seed": hasard.seed, "semaine": hasard.semaine},
        "poids": dict(config.POIDS),
        "note": round_half_up(note, 1),
        "confiance": confidence(note),
        "raisons": raisons,
        "prevision": prevision,
        "dividende_par_action": None if dividende_par_action is None else str(dividende_par_action),
        "cours": tech.details.get("cours"),
        "variation_jour_pct": day_change_pct(past),
        "date_cours": None if past.empty else past["date_seance"].iloc[-1].isoformat(),
    }
    return {
        "score_global": round(note, 2),
        "decision": conseil,
        "prevision_semaine_pct": None if prevision is None else prevision["central"],
        "details_piliers": json_safe(details),
    }


def day_change_pct(history: pd.DataFrame) -> float | None:
    """Variation entre les deux dernières clôtures, en %."""
    if history is None or len(history) < 2:
        return None
    last, previous = history["close"].iloc[-1], history["close"].iloc[-2]
    return round((float(last) / float(previous) - 1) * 100, 2) if previous else None


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def open_week_if_needed(repo, today: date, histories: Mapping[str, pd.DataFrame]) -> dict[str, Any] | None:
    """Lundi (ou première actualisation de la semaine) : nouvelle valeur de référence =
    valeur du portefeuille au dernier cours avant lundi (SPEC §11.1, RG-01)."""
    portfolio = repo.get_portfolio()
    monday = monday_of(today)
    if portfolio["date_ref_semaine"] >= monday:
        return None
    cash = portfolio["cash_disponible"]
    held: dict[str, int] = {}
    for tx in repo.get_transactions(portfolio["id"]):
        sign = 1 if tx["type_op"] == ACHAT else -1
        if tx["date_execution"].date() >= monday:
            cash += sign * tx["montant_total"]  # on annule les opérations de cette semaine
        else:
            held[tx["ticker"]] = held.get(tx["ticker"], 0) + sign * tx["quantite_entiere"]
    value = Decimal(str(cash))
    for ticker, quantity in held.items():
        history = histories.get(ticker)
        if quantity <= 0 or history is None or history.empty:
            continue
        before = history[pd.to_datetime(history["date_seance"]).dt.date < monday]
        if not before.empty:
            value += Decimal(quantity) * Decimal(str(before["close"].iloc[-1]))
    value = value.quantize(Decimal("0.01"))
    repo.update_portfolio_week(portfolio["id"], value, monday)
    return {"val_semaine_prec": str(value), "date_ref_semaine": monday.isoformat()}


def intraday_complete(repo, action_id: str, history: pd.DataFrame, now: datetime) -> bool:
    """Les bougies de 5 min des 20 derniers jours sont-elles (presque) toutes là ? On compte
    les bougies présentes et on les compare aux séances connues (hors aujourd'hui) : un trou
    laissé par une actualisation interrompue fait recharger le mois entier (D-15)."""
    since = now - timedelta(days=config.INTRADAY_HISTORIQUE_MIN_JOURS)
    if history.empty:
        return False
    days = pd.to_datetime(history["date_seance"]).dt.date
    sessions = int(((days >= since.date()) & (days < now.date())).sum())
    expected = sessions * config.INTRADAY_BOUGIES_PAR_SEANCE * config.INTRADAY_TAUX_MIN
    return sessions > 0 and repo.count_intraday(action_id, since) >= expected


def collect_stock(repo, collector: MarketCollector, action: dict[str, Any], now: datetime, news_api_key: str):
    """Collecte d'UNE action (cours, ratios, actualités). Lancée en parallèle pour les 5."""
    ticker, action_id = action["ticker"], action["id"]
    counts = {"cours": 0, "ratios": 0, "actualites": 0, "intraday": 0}
    errors: list[str] = []

    last = repo.last_history_date(action_id)
    try:
        rows = collector.history(ticker, None if last is None else last - timedelta(days=7))
        counts["cours"] = repo.upsert_history([{**r, "action_id": action_id} for r in rows])
    except Exception as error:
        errors.append(f"{ticker} cours : {type(error).__name__}: {error}")
    history = repo.get_history(action_id)

    dividend = action.get("dividende_estime") or None
    try:
        fundamentals = collector.fundamentals(ticker, history, now.date())
        rows = [{**r, "action_id": action_id} for r in fundamentals.exercices]
        counts["ratios"] = repo.save_ratios(action_id, rows)
        dividend = fundamentals.dividende_12_mois or dividend
    except Exception as error:
        errors.append(f"{ticker} ratios : {type(error).__name__}: {error}")

    try:
        articles, news_errors = collector.news(ticker, now, news_api_key)
        errors += [f"{ticker} {e}" for e in news_errors]
        since = now - timedelta(days=config.INFO_FENETRE_JOURS)
        counts["actualites"] = repo.insert_missing_articles(action_id, articles, since)
    except Exception as error:
        errors.append(f"{ticker} actualités : {type(error).__name__}: {error}")

    try:  # bougies de 5 min (graphiques 1 jour / 1 semaine) ; table créée par la migration 004
        rows = collector.intraday(
            ticker,
            config.INTRADAY_PERIODE if intraday_complete(repo, action_id, history, now) else config.INTRADAY_PERIODE_INITIALE,
        )
        counts["intraday"] = repo.upsert_intraday([{**r, "action_id": action_id} for r in rows])
    except Exception as error:
        errors.append(f"{ticker} intraday : {type(error).__name__}")

    price = float(history["close"].iloc[-1]) if not history.empty else _num(action.get("dernier_cours"))
    gathered = {"action": action, "history": history, "dividend": dividend, "price": price}
    return ticker, counts, errors, gathered


def refresh(repo, collector: MarketCollector, now: datetime | None = None, news_api_key: str = "") -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    today = now.date()
    report: dict[str, Any] = {"horodatage": now.isoformat(timespec="seconds"), "actions": {}, "erreurs": []}
    gathered: dict[str, dict[str, Any]] = {}

    # Les 5 collectes partent en même temps : ~10 s au lieu de ~40 s (attente réseau).
    actions = repo.get_actions()
    with ThreadPoolExecutor(max_workers=max(1, len(actions))) as pool:
        results = list(pool.map(lambda a: collect_stock(repo, collector, a, now, news_api_key), actions))
    for ticker, counts, errors, data in sorted(results, key=lambda r: r[0]):
        report["actions"][ticker] = counts
        report["erreurs"] += errors
        gathered[ticker] = data

    yields = {t: current_yield(g["dividend"], g["price"]) for t, g in gathered.items()}
    available = [y for y in yields.values() if y]
    average_yield = mean(available) if available else None

    scores = []
    since = now - timedelta(days=config.INFO_FENETRE_JOURS)
    for ticker, g in gathered.items():
        action = g["action"]
        result = score_stock(
            ticker,
            g["history"],
            repo.get_ratios(action["id"]),
            [a for a in repo.get_articles(action["id"], since)
             if market_data.is_relevant(ticker, a["titre"], a.get("resume"))],
            yields[ticker],
            average_yield,
            g["dividend"],
            now,
        )
        scores.append({**result, "action_id": action["id"], "date_calcul": now.isoformat()})
        update: dict[str, Any] = {"maj_le": now.isoformat()}
        if g["price"]:
            update["dernier_cours"] = Decimal(str(g["price"])).quantize(Decimal("0.01"))
        if g["dividend"] is not None:
            update["dividende_estime"] = g["dividend"]
        repo.update_action(action["id"], **update)
        report["actions"][ticker]["conseil"] = result["decision"]
        report["actions"][ticker]["note"] = result["details_piliers"]["note"]
    if scores:
        repo.insert_scores(scores)

    if any(r["intraday"] for r in report["actions"].values()):
        try:
            repo.purge_intraday(now - timedelta(days=config.INTRADAY_CONSERVATION_JOURS))
        except Exception as error:
            report["erreurs"].append(f"intraday (nettoyage) : {type(error).__name__}")

    report["semaine"] = open_week_if_needed(repo, today, {t: g["history"] for t, g in gathered.items()})
    return report
