"""Collecte des données externes — appelée UNIQUEMENT pendant une actualisation (ENF-02).

En bref :
- ``fetch_history`` : cours quotidiens (ouverture, plus haut, plus bas, clôture,
  volume) par yfinance ; 2 ans au premier passage (MM200 et 52 semaines), puis
  seulement les derniers jours ;
- ``fetch_fundamentals`` : chiffre d'affaires des deux derniers exercices et
  dividendes versés (yfinance) ; on en déduit le dividende par action de chaque
  année, le rendement, et le dividende attendu (12 derniers mois, SPEC §5.1) ;
- ``fetch_news`` : actualités des 7 derniers jours par Google News (RSS, en français)
  et NewsAPI ; chaque article reçoit sa note d'impact dès la collecte (SPEC §4.1).

Si une source est en panne, la fonction renvoie ce qu'elle a pu obtenir et note
l'erreur : les dernières données valides restent en base (UI §6.3).
"""

from __future__ import annotations

import html
import json
import logging
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import pandas as pd
import yfinance as yf

import config
from services.info_scoring import impact_score
from services.sentiment import is_announcement, sentiment

log = logging.getLogger(__name__)
USER_AGENT = "primeinvest/0.1 (outil d'aide a la decision)"


def _round(value: float | None, digits: int = 2) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(Decimal(str(value)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# Cours
# ---------------------------------------------------------------------------


def fetch_history(ticker: str, since: date | None) -> list[dict[str, Any]]:
    """Cours quotidiens depuis ``since`` (inclus), ou sur 2 ans si ``since`` est None."""
    yt = yf.Ticker(ticker)
    if since is None:
        raw = yt.history(period=f"{config.HISTORIQUE_INITIAL_ANNEES}y", auto_adjust=False)
    else:
        raw = yt.history(start=since.isoformat(), auto_adjust=False)
    rows = []
    for stamp, bar in raw.iterrows():
        if pd.isna(bar["Close"]):
            continue
        rows.append(
            {
                "date_seance": stamp.date().isoformat(),
                "open": _round(bar["Open"]),
                "high": _round(bar["High"]),
                "low": _round(bar["Low"]),
                "close": _round(bar["Close"]),
                "volume": None if pd.isna(bar["Volume"]) else int(bar["Volume"]),
            }
        )
    return rows


def fetch_intraday(ticker: str, period: str | None = None) -> list[dict[str, Any]]:
    """Bougies de 5 minutes (graphiques 1 jour / 1 semaine, D-12) : les 5 dernières séances,
    ou un mois au premier chargement (``period="1mo"``)."""
    raw = yf.Ticker(ticker).history(
        period=period or config.INTRADAY_PERIODE, interval=config.INTRADAY_INTERVALLE, auto_adjust=False
    )
    rows = []
    for stamp, bar in raw.iterrows():
        if pd.isna(bar["Close"]):
            continue
        rows.append(
            {
                "horodatage": stamp.tz_convert("UTC").isoformat(),
                "open": _round(bar["Open"]),
                "high": _round(bar["High"]),
                "low": _round(bar["Low"]),
                "close": _round(bar["Close"]),
                "volume": None if pd.isna(bar["Volume"]) else int(bar["Volume"]),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Ratios financiers
# ---------------------------------------------------------------------------


@dataclass
class Fundamentals:
    exercices: list[dict[str, Any]] = field(default_factory=list)  # du plus récent au plus ancien
    dividende_12_mois: Decimal | None = None


def dividends_by_year(dividends: pd.Series) -> dict[int, float]:
    """Dividende par action de chaque année = versement moyen de l'année × nombre habituel
    de versements par an. Évite les faux écarts quand un versement trimestriel glisse
    d'une année civile à l'autre (TotalEnergies : 5 versements datés en 2025)."""
    if dividends is None or dividends.empty:
        return {}
    by_year = dividends.groupby(dividends.index.year)
    usual = max(1, round(float(by_year.count().median())))
    return {int(y): float(v) * usual for y, v in by_year.mean().items()}


def trailing_dividend(dividends: pd.Series, today: date) -> Decimal | None:
    """Dividende par action versé sur les 12 derniers mois (SPEC §5.1)."""
    if dividends is None or dividends.empty:
        return None
    start = pd.Timestamp(today - timedelta(days=365), tz=dividends.index.tz)
    total = float(dividends[dividends.index > start].sum())
    return Decimal(_round(total)) if total > 0 else None


def build_exercises(
    revenue: dict[date, float], dividends: dict[int, float], year_end_close: dict[int, float]
) -> list[dict[str, Any]]:
    """Une ligne par exercice : CA, dividende par action versé dans l'année civile de
    l'exercice, rendement = dividende / cours de fin d'année."""
    rows = []
    for end in sorted(revenue, reverse=True)[:2]:
        dpa = dividends.get(end.year)
        close = year_end_close.get(end.year)
        rendement = dpa / close * 100 if dpa and close else None
        rows.append(
            {
                "date_maj": end.isoformat(),
                "chiffre_affaires": _round(revenue[end]),
                "dividende_par_action": _round(dpa),
                "rendement_pct": _round(rendement),
            }
        )
    return rows


def fetch_fundamentals(ticker: str, history: pd.DataFrame, today: date) -> Fundamentals:
    yt = yf.Ticker(ticker)
    dividends = yt.dividends
    revenue: dict[date, float] = {}
    try:
        income = yt.income_stmt
        if "Total Revenue" in income.index:
            for stamp, value in income.loc["Total Revenue"].dropna().items():
                revenue[pd.Timestamp(stamp).date()] = float(value)
    except Exception as error:  # source indisponible : on garde les données en base
        log.warning("chiffre d'affaires indisponible pour %s : %s", ticker, error)
    year_end_close: dict[int, float] = {}
    if not history.empty:
        closes = history.assign(year=pd.to_datetime(history["date_seance"]).dt.year)
        year_end_close = closes.groupby("year")["close"].last().astype(float).to_dict()
    return Fundamentals(
        exercices=build_exercises(revenue, dividends_by_year(dividends), year_end_close),
        dividende_12_mois=trailing_dividend(dividends, today),
    )


# ---------------------------------------------------------------------------
# Actualités
# ---------------------------------------------------------------------------


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text or ""))).strip()


def _plain(text: str) -> str:
    import unicodedata

    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def is_relevant(ticker: str, titre: str, resume: str | None = None) -> bool:
    """L'article parle-t-il vraiment de l'entreprise ? (nom dans le titre ou le résumé,
    et pas une simple page de cotation)."""
    text = _plain(f"{titre} {resume or ''}")
    if any(noise in text for noise in config.NEWS_BRUIT):
        return False
    return any(keyword in text for keyword in config.NEWS_MOTS_CLES[ticker])


def score_article(titre: str, resume: str | None) -> float:
    text = f"{titre}. {resume or ''}"
    return round(impact_score(sentiment(text), is_announcement(text)), 2)


def _article(titre: str, resume: str | None, source: str | None, url: str | None, published: datetime):
    titre = _clean(titre)
    resume = _clean(resume) or None
    return {
        "titre": titre,
        "resume": resume,
        "source": (source or "")[:100] or None,
        "url": url,
        "date_pub": published,
        "score_impact": score_article(titre, resume),
    }


def parse_google_news(feed: Any, now: datetime) -> list[dict[str, Any]]:
    start = now - timedelta(days=config.INFO_FENETRE_JOURS)
    articles = []
    for entry in feed.entries:
        published = parsedate_to_datetime(entry.published).astimezone(timezone.utc)
        if not start <= published <= now:
            continue
        source = entry.get("source", {}).get("title")
        titre = entry.title
        if source and titre.endswith(f" - {source}"):
            titre = titre[: -len(source) - 3]
        resume = _clean(entry.get("summary"))
        if resume.startswith(_clean(titre)[:40]):
            resume = None  # Google répète le titre dans le résumé
        articles.append(_article(titre, resume, source, entry.link, published))
    return articles[: config.NEWS_MAX_ARTICLES_PAR_SOURCE]


def parse_newsapi(payload: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
    start = now - timedelta(days=config.INFO_FENETRE_JOURS)
    articles = []
    for item in payload.get("articles", []):
        if not item.get("title") or item["title"] == "[Removed]":
            continue
        published = datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
        if start <= published <= now:
            articles.append(
                _article(item["title"], item.get("description"), item["source"].get("name"), item.get("url"), published)
            )
    return articles[: config.NEWS_MAX_ARTICLES_PAR_SOURCE]


def fetch_news(ticker: str, now: datetime, news_api_key: str) -> tuple[list[dict[str, Any]], list[str]]:
    query = config.NEWS_QUERIES[ticker]
    articles: list[dict[str, Any]] = []
    errors: list[str] = []

    rss = (
        "https://news.google.com/rss/search?"
        + urllib.parse.urlencode({"q": f"{query} when:7d", "hl": "fr", "gl": "FR", "ceid": "FR:fr"})
    )
    try:
        articles += parse_google_news(feedparser.parse(rss, agent=USER_AGENT), now)
    except Exception as error:
        errors.append(f"Google News : {error}")

    if news_api_key:
        params = urllib.parse.urlencode(
            {
                "q": query,
                "searchIn": "title,description",
                "from": (now - timedelta(days=config.INFO_FENETRE_JOURS)).date().isoformat(),
                "sortBy": "publishedAt",
                "pageSize": config.NEWS_MAX_ARTICLES_PAR_SOURCE,
            }
        )
        request = urllib.request.Request(
            f"https://newsapi.org/v2/everything?{params}",
            headers={"X-Api-Key": news_api_key, "User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(request, timeout=config.HTTP_TIMEOUT_SECONDES) as response:
                articles += parse_newsapi(json.load(response), now)
        except Exception as error:  # la clé n'apparaît jamais dans le message
            errors.append(f"NewsAPI : {type(error).__name__}")
    return [a for a in articles if is_relevant(ticker, a["titre"], a["resume"])], errors
