"""Collecte et actualisation (ENF-02, SPEC §1.3, §11.1) — sans réseau ni base réelle."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from services import market_data
from services.refresh_service import monday_of, open_week_if_needed, refresh, score_stock
from tests.fakes import FakeCollector, FakeRepository

NOW = datetime(2026, 11, 25, 17, 0, tzinfo=timezone.utc)


def articles_for(now):
    return {
        "DSY.PA": [
            {"titre": "Dassault Systèmes annonce de nouveaux contrats", "resume": None, "source": "Presse",
             "url": "https://ex.fr/1", "date_pub": now - timedelta(days=1), "score_impact": 80.0},
            {"titre": "Un analyste abaisse son objectif sur Dassault Systèmes", "resume": None, "source": "Agence",
             "url": "https://ex.fr/2", "date_pub": now - timedelta(days=4), "score_impact": 30.0},
        ]
    }


def test_refresh_fills_history_scores_and_updates_actions():
    repo = FakeRepository()
    report = refresh(repo, FakeCollector(NOW.date(), articles=articles_for(NOW)), NOW, "")
    assert report["erreurs"] == []
    assert len(repo.scores) == 5
    assert {s["decision"] for s in repo.scores} <= {"ACHAT", "VENTE", "RIEN"}  # RG-02
    for score in repo.scores:
        details = score["details_piliers"]
        assert 2 <= len(details["raisons"]) <= 4  # RG-03
        assert details["prevision"] is not None  # 2 ans d'historique
        assert set(details["poids"]) == {"infos", "tech", "ratios", "hasard"}
        assert "seed" in details["hasard"]
    dsy = repo.action_by_ticker("DSY.PA")
    assert dsy["dividende_estime"] == Decimal("0.29")
    assert dsy["dernier_cours"] == Decimal(repo.history[dsy["id"]][max(repo.history[dsy["id"]])]["close"])
    dsy_score = next(s for s in repo.scores if s["action_id"] == dsy["id"])
    assert dsy_score["details_piliers"]["infos"]["score"] == pytest.approx(66.9, abs=0.05)
    assert report["actions"]["DSY.PA"]["actualites"] == 2


def test_refresh_loads_two_years_first_then_only_recent_days():
    repo = FakeRepository()
    collector = FakeCollector(NOW.date())
    refresh(repo, collector, NOW)
    assert collector.calls[0] == ("AI.PA", None)  # premier passage : 2 ans
    refresh(repo, collector, NOW + timedelta(hours=1))
    since = collector.calls[5][1]
    assert since is not None and (NOW.date() - since).days <= 10


def test_refresh_is_idempotent_for_ratios_and_articles():
    repo = FakeRepository()
    collector = FakeCollector(NOW.date(), articles=articles_for(NOW))
    refresh(repo, collector, NOW)
    refresh(repo, collector, NOW + timedelta(hours=1))
    assert len(repo.ratios) == 10  # 5 actions × 2 exercices, pas de doublon
    assert len(repo.articles) == 2
    assert len(repo.scores) == 10  # une ligne par calcul


def test_refresh_survives_source_failures():
    repo = FakeRepository()
    report = refresh(repo, FakeCollector(NOW.date(), fail={"history", "fundamentals", "news"}), NOW)
    assert any("cours" in e for e in report["erreurs"])
    assert any("ratios" in e for e in report["erreurs"])
    assert any("Google News" in e for e in report["erreurs"])
    assert len(repo.scores) == 5  # notes neutres mais conseils toujours rendus (RG-02)
    assert all(s["details_piliers"]["prevision"] is None for s in repo.scores)


def test_open_week_on_first_refresh_of_a_new_week():
    repo = FakeRepository(cash="450027.20", ref_day=date(2026, 11, 16))
    collector = FakeCollector(NOW.date())
    dsy = repo.action_by_ticker("DSY.PA")
    repo.execute_transaction(repo.portfolio["id"], dsy["id"], "ACHAT", 1436, {},
                             when=datetime(2026, 11, 18, 14, 5, tzinfo=timezone.utc))
    report = refresh(repo, collector, NOW)
    assert report["semaine"]["date_ref_semaine"] == "2026-11-23"
    history = repo.get_history(dsy["id"])
    friday_close = history[history["date_seance"] < date(2026, 11, 23)]["close"].iloc[-1]
    expected = (repo.portfolio["cash_disponible"] + 1436 * Decimal(str(friday_close))).quantize(Decimal("0.01"))
    assert repo.portfolio["val_semaine_prec"] == expected
    assert refresh(repo, collector, NOW + timedelta(hours=1))["semaine"] is None  # déjà ouverte


def test_open_week_ignores_this_weeks_operations():
    repo = FakeRepository(ref_day=date(2026, 11, 16))
    refresh(repo, FakeCollector(NOW.date()), NOW - timedelta(days=7))  # historique en place
    repo.portfolio["date_ref_semaine"] = date(2026, 11, 16)
    dsy = repo.action_by_ticker("DSY.PA")
    repo.execute_transaction(repo.portfolio["id"], dsy["id"], "ACHAT", 100, {},
                             when=datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc))
    histories = {"DSY.PA": repo.get_history(dsy["id"])}
    result = open_week_if_needed(repo, NOW.date(), histories)
    assert Decimal(result["val_semaine_prec"]) == Decimal("500000.00")


def test_monday_of():
    assert monday_of(date(2026, 11, 25)) == date(2026, 11, 23)
    assert monday_of(date(2026, 11, 23)) == date(2026, 11, 23)


def test_score_stock_without_any_data_is_neutral():
    empty = pd.DataFrame(columns=["date_seance", "open", "high", "low", "close", "volume"])
    result = score_stock("DSY.PA", empty, [], [], None, None, None, NOW)
    assert result["details_piliers"]["infos"]["message"] == "aucune actualité récente"
    assert result["prevision_semaine_pct"] is None
    assert result["decision"] in {"ACHAT", "VENTE", "RIEN"}


# --- Analyse des sources (formats yfinance, RSS, NewsAPI) ------------------------------


def test_build_exercises_and_dividends():
    dividends = pd.Series(
        [0.23, 0.26, 0.27],
        index=pd.to_datetime(["2024-05-27", "2025-05-26", "2026-05-27"]).tz_localize("Europe/Paris"),
    )
    by_year = market_data.dividends_by_year(dividends)
    assert by_year == {2024: 0.23, 2025: 0.26, 2026: 0.27}
    assert market_data.trailing_dividend(dividends, date(2026, 11, 25)) == Decimal("0.27")
    rows = market_data.build_exercises(
        {date(2025, 12, 31): 6.2357e9, date(2024, 12, 31): 6.2136e9, date(2023, 12, 31): 5.9e9},
        by_year,
        {2025: 26.0, 2024: 23.0},
    )
    assert [r["date_maj"] for r in rows] == ["2025-12-31", "2024-12-31"]
    assert rows[0]["dividende_par_action"] == "0.26"
    assert rows[0]["rendement_pct"] == "1.00"
    assert market_data.trailing_dividend(pd.Series(dtype=float), date(2026, 1, 1)) is None


def test_parse_google_news_keeps_last_7_days_and_strips_source():
    feed = SimpleNamespace(entries=[
        {"title": "Hermès International clôture en forte baisse - Boursier.com",
         "published": "Fri, 20 Nov 2026 16:42:09 GMT", "link": "https://g.co/1",
         "summary": "<a>Hermès International clôture en forte baisse</a>",
         "source": {"title": "Boursier.com"}},
        {"title": "Vieux - Le Monde", "published": "Mon, 02 Nov 2026 08:00:00 GMT",
         "link": "https://g.co/2", "summary": "", "source": {"title": "Le Monde"}},
    ])
    feed.entries = [SimpleNamespace(**e, get=e.get) for e in feed.entries]
    articles = market_data.parse_google_news(feed, NOW)
    assert len(articles) == 1
    assert articles[0]["titre"] == "Hermès International clôture en forte baisse"
    assert articles[0]["resume"] is None
    assert articles[0]["score_impact"] < 50


def test_parse_newsapi_skips_removed_and_old_items():
    payload = {"articles": [
        {"title": "Air Liquide signe un contrat record", "description": "Croissance solide",
         "source": {"name": "Les Echos"}, "url": "https://x/1", "publishedAt": "2026-11-24T08:00:00Z"},
        {"title": "[Removed]", "source": {"name": "?"}, "publishedAt": "2026-11-24T08:00:00Z"},
        {"title": "Ancien", "source": {"name": "?"}, "url": "u", "publishedAt": "2026-10-01T08:00:00Z"},
    ]}
    articles = market_data.parse_newsapi(payload, NOW)
    assert len(articles) == 1 and articles[0]["score_impact"] > 50


def test_fetch_history_formats_yfinance_rows(monkeypatch):
    frame = pd.DataFrame(
        {"Open": [22.17, 22.32], "High": [22.5, 22.4], "Low": [22.0, 22.1], "Close": [22.360001, float("nan")],
         "Volume": [7544849, 1]},
        index=pd.to_datetime(["2026-11-24", "2026-11-25"]).tz_localize("Europe/Paris"),
    )
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: SimpleNamespace(history=lambda **kw: frame))
    rows = market_data.fetch_history("DSY.PA", None)
    assert rows == [{"date_seance": "2026-11-24", "open": "22.17", "high": "22.50", "low": "22.00",
                     "close": "22.36", "volume": 7544849}]


def test_json_safe_removes_nan_and_numpy_types():
    import numpy as np

    from services.refresh_service import json_safe

    cleaned = json_safe({"a": float("nan"), "b": np.float64(1.5), "c": [np.int64(3), None], "d": True})
    assert cleaned == {"a": None, "b": 1.5, "c": [3, None], "d": True}
    assert type(cleaned["b"]) is float and type(cleaned["c"][0]) is int


def test_quarterly_dividends_are_annualized_by_usual_frequency():
    dates = ["2024-01-02", "2024-03-20", "2024-06-19", "2024-09-25",
             "2025-01-02", "2025-03-26", "2025-06-19", "2025-10-01", "2025-12-31"]
    values = [0.74, 0.74, 0.79, 0.79, 0.79, 0.79, 0.85, 0.85, 0.85]
    series = pd.Series(values, index=pd.to_datetime(dates).tz_localize("Europe/Paris"))
    by_year = market_data.dividends_by_year(series)
    assert by_year[2024] == pytest.approx(3.06)
    assert by_year[2025] == pytest.approx(0.826 * 4)  # 5 versements datés en 2025, pas +35 %


@pytest.mark.parametrize(
    ("ticker", "titre", "attendu"),
    [
        ("RMS.PA", "Hermès International finit en légère hausse", True),
        ("RMS.PA", "Dossier de Bourse d'Anthropic : les confessions d'un géant de l'IA", False),
        ("CAP.PA", "CAPGEMINI Cours Action CAP, Cotation Bourse Euronext Paris", False),
        ("DSY.PA", "Dassault Systèmes clôture en légère hausse", True),
    ],
)
def test_news_relevance_filter(ticker, titre, attendu):
    assert market_data.is_relevant(ticker, titre) is attendu


def test_refresh_stores_intraday_bars_and_purges_old_ones():
    repo = FakeRepository()
    dsy = repo.action_by_ticker("DSY.PA")["id"]
    repo.intraday[dsy]["2026-11-01T09:00:00+00:00"] = {
        "action_id": dsy, "horodatage": "2026-11-01T09:00:00+00:00", "close": "1"}
    report = refresh(repo, FakeCollector(NOW.date()), NOW)
    assert report["actions"]["DSY.PA"]["intraday"] == 510
    assert "2026-11-01T09:00:00+00:00" not in repo.intraday[dsy]  # plus de 10 jours : supprimée
    assert len(repo.intraday[dsy]) == 510


def test_fetch_intraday_formats_yfinance_rows(monkeypatch):
    frame = pd.DataFrame(
        {"Open": [22.1], "High": [22.2], "Low": [22.0], "Close": [22.15], "Volume": [1200]},
        index=pd.to_datetime(["2026-11-26 09:05"]).tz_localize("Europe/Paris"),
    )
    monkeypatch.setattr(market_data.yf, "Ticker", lambda t: SimpleNamespace(history=lambda **kw: frame))
    assert market_data.fetch_intraday("DSY.PA") == [{
        "horodatage": "2026-11-26T08:05:00+00:00", "open": "22.10", "high": "22.20", "low": "22.00",
        "close": "22.15", "volume": 1200,
    }]
