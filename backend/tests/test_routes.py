"""Les 6 routes de l'API et les tests de recette REC-1 à REC-4 (CdCF §6.2, CLAUDE.md §7).

L'API tourne sur une fausse base en mémoire remplie par une actualisation simulée :
aucun appel à Supabase ni à Internet.
"""

import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import config
from config import Settings
from main import create_app
from routers import deps, stocks
from services.refresh_service import refresh
from tests.fakes import FakeCollector, FakeRepository
from tools.stress_test import shocked_level

NOW = datetime(2026, 11, 25, 17, 0, tzinfo=timezone.utc)


@pytest.fixture
def repo():
    repo = FakeRepository()
    refresh(repo, FakeCollector(NOW.date()), NOW)
    repo.clock = NOW
    return repo


@pytest.fixture
def api(repo):
    app = create_app(Settings("", "", "", ("http://localhost:5173",)))
    app.dependency_overrides[deps.get_repo] = lambda: repo
    app.dependency_overrides[deps.get_now] = lambda: NOW
    app.dependency_overrides[deps.get_collector] = lambda: FakeCollector(NOW.date())
    stocks._last_refresh["at"] = 0.0
    return TestClient(app)


def set_price(repo, ticker, price):
    repo.action_by_ticker(ticker)["dernier_cours"] = Decimal(price)


def force_decision(repo, ticker, decision):
    action_id = repo.action_by_ticker(ticker)["id"]
    repo.latest_scores()[action_id]["decision"] = decision


def simulate(api, ticker="DSY.PA", operation="ACHAT", montant=50000):
    response = api.post("/api/simulate", json={"tickers": [ticker], "operation": operation, "montant_eur": montant})
    assert response.status_code == 200, response.text
    return response.json()


def confirm(api, result, date_conseil, ticker="DSY.PA"):
    return api.post("/api/transactions", json={
        "ticker": ticker, "operation": result["operation"], "quantite": result["quantite_entiere"],
        "cours_simule": result["cours_actuel"], "date_conseil": date_conseil,
    })


# --- Recette -------------------------------------------------------------------------


def test_rec1_five_stocks_have_decision_forecast_dividend(api):
    body = api.get("/api/dashboard").json()
    assert [a["ticker"] for a in body["actions"]] == list(config.TICKERS)
    for stock in body["actions"]:
        assert stock["conseil"] in {"ACHAT", "VENTE", "RIEN"}  # RG-02
        assert set(stock["prevision_semaine_pct"]) == {"defavorable", "central", "favorable"}
        assert stock["dividende_par_action"] > 0
    assert "ne garantit pas" in body["mention"]  # ENF-03


def test_rec2_simulate_then_record_round_trip(api, repo):
    set_price(repo, "DSY.PA", "34.80")
    started = time.perf_counter()
    sim = simulate(api)
    result = sim["resultats"][0]
    assert sim["enregistre"] is False and repo.transactions == []  # la simulation n'écrit rien
    response = confirm(api, result, sim["date_conseil"])
    elapsed = time.perf_counter() - started
    assert response.status_code == 200, response.text
    assert elapsed < 2  # ENF-02
    assert response.json()["cash_disponible"] == 500000 - 49972.80
    dashboard = api.get("/api/dashboard").json()
    dsy = next(a for a in dashboard["actions"] if a["ticker"] == "DSY.PA")
    assert dsy["detenues"] == 1436 and dsy["dividende_estime_eur"] == 416.44
    stored = repo.transactions[0]["conseil_algo"]
    assert stored["seed"] and stored["raisons"]  # le conseil est rejouable (DCT §9.1)


def test_rec3_every_buy_has_reasons_and_info_tab(api, repo):
    force_decision(repo, "AI.PA", "ACHAT")
    for ticker in config.TICKERS:
        body = api.get(f"/api/stocks/{ticker}").json()
        assert 2 <= len(body["conseil"]["raisons"]) <= 4  # RG-03
        assert "actualites" in body["infos"] and "ratios" in body["infos"]
        assert len(body["infos"]["piliers"]) == 4
    assert api.get("/api/stocks/AI.PA").json()["conseil"]["decision"] == "ACHAT"


def test_rec4_guard_triggers_at_minus_10pct(api, repo):
    # Portefeuille de la SPEC §11.2 : 400 000 € investis, 100 000 € de cash, baisse de 12,5 %
    variation, level = shocked_level(
        Decimal("100000"), {"DSY.PA": 10000}, {"DSY.PA": Decimal("40")}, Decimal("500000"), 12.5
    )
    assert level == "ATTEINT"
    # Même situation dans l'API : la valeur de référence du lundi est 10,4 % au-dessus
    repo.portfolio["val_semaine_prec"] = (Decimal("500000") / Decimal("0.896")).quantize(Decimal("0.01"))
    body = api.get("/api/dashboard").json()
    assert body["niveau_alerte"] == "ATTEINT" and body["alerte_perte_10pct"] is True
    assert body["actions"][0]["raisons"][0].startswith("Limite de perte atteinte")
    force_decision(repo, "DSY.PA", "ACHAT")
    assert simulate(api)["resultats"][0]["verdict"] == "NE_RIEN_FAIRE"  # plus aucun achat conseillé


def test_rg05_dct_example_1436_shares(api, repo):
    set_price(repo, "DSY.PA", "34.80")
    result = simulate(api)["resultats"][0]
    assert result["quantite_entiere"] == 1436
    assert result["montant_reel_investi"] == 49972.80
    assert result["reliquat_cash"] == 27.20
    assert result["dividende_annuel_estime_eur"] == 416.44
    assert result["cash_apres_operation"] == 450027.20


def test_v14_transactions_atomic_on_insufficient_cash(api, repo):
    set_price(repo, "DSY.PA", "34.80")
    sim = simulate(api)
    repo.portfolio["cash_disponible"] = Decimal("1000.00")  # le cash a baissé entre-temps
    response = confirm(api, sim["resultats"][0], sim["date_conseil"])
    assert response.status_code == 400
    assert "rien n'a été enregistré" in response.json()["detail"]
    assert repo.transactions == [] and repo.portfolio["cash_disponible"] == Decimal("1000.00")


# --- Simulateur ------------------------------------------------------------------------


def test_simulate_refused_operation_is_shown_with_its_reason(api):
    result = simulate(api, montant=600000)["resultats"][0]
    assert result["verdict"] == "REFUSE"
    assert result["raisons"][0].startswith("Vous disposez de")


def test_simulate_several_tickers_applies_amount_to_each(api):
    body = api.post("/api/simulate", json={
        "tickers": ["DSY.PA", "AI.PA", "TTE.PA"], "operation": "ACHAT", "montant_eur": 200000,
    }).json()
    assert len(body["resultats"]) == 3
    assert all(r["montant_reel_investi"] <= 200000 for r in body["resultats"])
    assert "dépasse votre cash" in body["avertissement"]


def test_simulate_accepts_dct_single_ticker_contract(api):
    response = api.post("/api/simulate", json={"ticker": "DSY.PA", "operation": "ACHAT", "montant_eur": 1000})
    assert response.status_code == 200 and response.json()["resultats"][0]["ticker"] == "DSY.PA"


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"tickers": ["XXX.PA"], "operation": "ACHAT", "montant_eur": 1000}, 404),
        ({"tickers": ["DSY.PA"], "operation": "ACHAT", "montant_eur": -5}, 422),
        ({"tickers": ["DSY.PA"], "operation": "PRET", "montant_eur": 100}, 422),
        ({"tickers": [], "operation": "ACHAT", "montant_eur": 100}, 422),
    ],
)
def test_simulate_input_errors(api, payload, status):
    assert api.post("/api/simulate", json=payload).status_code == status


# --- Enregistrement ----------------------------------------------------------------------


def test_transaction_rejected_when_advice_older_than_5_minutes(api, repo):
    sim = simulate(api)
    old = (NOW - timedelta(minutes=6)).isoformat()
    response = confirm(api, sim["resultats"][0], old)
    assert response.status_code == 400 and "5 minutes" in response.json()["detail"]
    assert repo.transactions == []


def test_transaction_rejected_when_price_changed(api, repo):
    sim = simulate(api)
    set_price(repo, "DSY.PA", "99.99")
    response = confirm(api, sim["resultats"][0], sim["date_conseil"])
    assert response.status_code == 400 and "cours a changé" in response.json()["detail"]


def test_sell_more_than_held_is_refused_by_the_database_check(api, repo):
    price = float(repo.action_by_ticker("DSY.PA")["dernier_cours"])
    response = api.post("/api/transactions", json={
        "ticker": "DSY.PA", "operation": "VENTE", "quantite": 5, "cours_simule": price,
        "date_conseil": NOW.isoformat(),
    })
    assert response.status_code == 400 and "pas assez d'actions" in response.json()["detail"]


def test_transaction_unknown_ticker_is_404(api):
    response = api.post("/api/transactions", json={
        "ticker": "ABC.PA", "operation": "ACHAT", "quantite": 1, "cours_simule": 10, "date_conseil": NOW.isoformat(),
    })
    assert response.status_code == 404


# --- Fiche action -----------------------------------------------------------------------


def test_stock_detail_one_call_feeds_both_tabs(api, repo):
    body = api.get("/api/stocks/dsy.pa").json()
    assert body["entete"]["ticker"] == "DSY.PA" and body["entete"]["place"] == "Euronext Paris"
    series = body["graphique"]["series"]
    assert 240 <= len(series) <= 262  # un an de séances
    assert {"mm20", "mm200", "boll_haut", "rsi", "macd_hist"} <= set(series[-1])
    assert series[-1]["mm200"] is not None
    assert body["conseil"]["seuil_achat"] == 60 and body["conseil"]["seuil_vente"] == 40
    assert body["prevision"]["disponible"] is True and body["prevision"]["eur"] is None  # aucune action détenue
    assert [p["poids"] for p in body["infos"]["piliers"]] == [0.40, 0.25, 0.25, 0.10]
    assert len(body["infos"]["ratios"]["exercices"]) == 2


def test_stock_detail_lists_relevant_recent_news(api, repo):
    action = repo.action_by_ticker("DSY.PA")
    repo.articles += [
        {"action_id": action["id"], "titre": "Dassault Systèmes signe un contrat record", "resume": None,
         "source": "Presse", "url": "u1", "date_pub": NOW - timedelta(hours=5), "score_impact": 80},
        {"action_id": action["id"], "titre": "Sans rapport avec l'entreprise", "resume": None,
         "source": "?", "url": "u2", "date_pub": NOW - timedelta(hours=5), "score_impact": 20},
    ]
    news = api.get("/api/stocks/DSY.PA").json()["infos"]["actualites"]
    assert [n["titre"] for n in news] == ["Dassault Systèmes signe un contrat record"]
    assert news[0]["age"] == "Il y a 5 heures" and news[0]["type"] == "Annonce officielle"


def test_stock_detail_unknown_ticker_is_404(api):
    response = api.get("/api/stocks/XXX.PA")
    assert response.status_code == 404 and "inconnue" in response.json()["detail"]


# --- Historique -------------------------------------------------------------------------


def test_history_after_buy_and_sell(api, repo):
    set_price(repo, "CAP.PA", "140.10")
    cap = repo.action_by_ticker("CAP.PA")["id"]
    repo.execute_transaction(repo.portfolio["id"], cap, "ACHAT", 300, {"conseil": "ACHAT"},
                             when=NOW - timedelta(days=20))
    set_price(repo, "CAP.PA", "146.20")
    repo.execute_transaction(repo.portfolio["id"], cap, "VENTE", 300, {"conseil": "VENTE"},
                             when=NOW - timedelta(days=12))
    body = api.get("/api/portfolio/history", params={"periode": "1m"}).json()
    assert body["bilan"]["plus_values_realisees"] == 1830.00  # maquette Historique
    assert body["bilan"]["nb_achats"] == 1 and body["bilan"]["nb_ventes"] == 1
    assert body["transactions"][0]["operation"] == "VENTE"  # plus récente d'abord
    assert body["transactions"][0]["plus_ou_moins_value"] == 1830.00
    assert body["transactions"][1]["conseil_donne"] == "ACHAT"
    assert len(body["courbe"]) >= 20 and body["courbe"][-1]["valeur"] == 501830.00
    assert len(body["marqueurs"]) == 2


def test_history_pagination_filter_and_periods(api, repo):
    dsy = repo.action_by_ticker("DSY.PA")["id"]
    for day in range(12):
        repo.execute_transaction(repo.portfolio["id"], dsy, "ACHAT", 1, {}, when=NOW - timedelta(days=day + 1))
    page2 = api.get("/api/portfolio/history", params={"periode": "1m", "page": 2, "taille": 5}).json()
    assert page2["pagination"] == {"page": 2, "taille": 5, "total": 12, "pages": 3}
    assert len(page2["transactions"]) == 5
    week = api.get("/api/portfolio/history", params={"periode": "1s"}).json()
    assert week["bilan"]["nb_operations"] == 7
    other = api.get("/api/portfolio/history", params={"ticker": "AI.PA"}).json()
    assert other["transactions"] == []
    assert api.get("/api/portfolio/history", params={"periode": "2a"}).status_code == 422


def test_history_without_operations_still_has_a_curve(api):
    body = api.get("/api/portfolio/history", params={"periode": "1s"}).json()
    assert body["courbe"] and all(point["valeur"] == 500000 for point in body["courbe"])


# --- Actualisation ----------------------------------------------------------------------


def test_refresh_route_then_rate_limited(api, repo):
    before = len(repo.scores)
    first = api.post("/api/market/refresh")
    assert first.status_code == 200 and len(repo.scores) == before + 5
    second = api.post("/api/market/refresh")
    assert second.status_code == 429 and "Retry-After" in second.headers
