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
from routers import deps, refresh_control
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
    app.dependency_overrides[deps.get_news_analyzer] = lambda: None  # jamais d'appel au modèle
    refresh_control.reset()
    refresh_control.last_refresh["at"] = time.monotonic()  # données fraîches : pas d'actualisation auto
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
    assert "ne garantissent pas" in body["mention"]  # ENF-03, D-25


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
    refresh_control.last_refresh["at"] = 0.0
    before = len(repo.scores)
    first = api.post("/api/market/refresh", params={"attendre": "true"})
    assert first.status_code == 200 and first.json()["statut"] == "termine"
    assert len(repo.scores) == before + 5
    second = api.post("/api/market/refresh")
    assert second.status_code == 429 and "Retry-After" in second.headers


def test_refresh_runs_in_background_and_reports_status(api, repo):
    refresh_control.last_refresh["at"] = 0.0
    before = len(repo.scores)
    response = api.post("/api/market/refresh")
    assert response.status_code == 202 and response.json()["statut"] == "lance"
    status = api.get("/api/market/refresh/status").json()  # TestClient attend la tâche de fond
    assert status["en_cours"] is False and status["termine_le"] and status["erreur"] is None
    assert set(status["rapport"]["actions"]) == set(config.TICKERS)
    assert len(repo.scores) == before + 5


def test_refresh_already_running_is_not_started_twice(api):
    refresh_control.state["en_cours"] = True
    response = api.post("/api/market/refresh")
    assert response.status_code == 202 and response.json()["statut"] == "en_cours"


def test_newsapi_called_at_most_every_15_minutes(monkeypatch):
    monkeypatch.setenv("NEWS_API_KEY", "cle")
    refresh_control.last_newsapi["at"] = 0.0
    assert refresh_control.news_key() == "cle"
    assert refresh_control.news_key() == ""  # deuxième actualisation juste après : pas de NewsAPI


def test_threshold_change_applies_immediately_without_refresh(api, repo, monkeypatch):
    """D-11 : le conseil est relu avec les seuils actuels (TotalEnergies à 55,2 → ACHAT à 55/45)."""
    action_id = repo.action_by_ticker("TTE.PA")["id"]
    score = repo.latest_scores()[action_id]
    score["score_global"] = 55.2
    score["decision"] = "RIEN"  # enregistré avec 60 / 40
    before = api.get("/api/stocks/TTE.PA").json()["conseil"]
    assert before["decision"] == "RIEN" and before["seuil_achat"] == 60
    monkeypatch.setattr(config, "SEUIL_ACHAT", 55.0)
    monkeypatch.setattr(config, "SEUIL_VENTE", 45.0)
    after = api.get("/api/stocks/TTE.PA").json()["conseil"]
    assert after["decision"] == "ACHAT" and after["seuil_achat"] == 55
    assert not any("sous le seuil" in r for r in after["raisons"])
    dashboard = api.get("/api/dashboard").json()
    assert next(a for a in dashboard["actions"] if a["ticker"] == "TTE.PA")["conseil"] == "ACHAT"


# --- Graphiques 1 jour / 1 semaine (D-12) ------------------------------------------------


def test_stock_detail_has_intraday_day_and_week_views(api):
    intraday = api.get("/api/stocks/DSY.PA").json()["graphique"]["intraday"]
    assert intraday["disponible"] is True
    day, week = intraday["jour"], intraday["semaine"]
    assert len(day) == 102  # une séance de 9 h à 17 h 30, bougies de 5 min
    assert day[0]["time"] % 86400 == 9 * 3600  # 9 h 00 affiché à l'heure de Paris
    assert 80 <= len(week) <= 90  # 5 séances, bougies de 30 min
    assert all(b["time"] < a["time"] for b, a in zip(week, week[1:]))
    assert {"open", "close", "mm20", "rsi", "macd_hist"} <= set(day[-1])


def test_intraday_indicators_start_with_the_first_candle(api):
    """D-14 : les indicateurs sont calculés sur l'historique, pas seulement sur les bougies
    affichées — toutes les courbes existent dès la première bougie de 1J et de 1S."""
    intraday = api.get("/api/stocks/DSY.PA").json()["graphique"]["intraday"]
    for view in ("jour", "semaine"):
        first = intraday[view][0]
        for key in ("mm20", "mm50", "mm200", "boll_haut", "boll_bas", "rsi", "macd", "macd_signal"):
            assert first[key] is not None, (view, key)


def test_intraday_unavailable_until_migration_004(api, repo):
    repo.intraday_table_exists = False
    refresh_control.last_refresh["at"] = 0.0
    report = api.post("/api/market/refresh", params={"attendre": "true"}).json()
    assert any("intraday" in e for e in report["erreurs"])
    assert len(report["actions"]) == 5  # le reste de l'actualisation a fonctionné
    body = api.get("/api/stocks/DSY.PA").json()["graphique"]["intraday"]
    assert body == {"disponible": False, "jour": [], "semaine": [], "derniere_bougie": None}


# --- Actualisation automatique à la consultation (D-13) ----------------------------------


def test_dashboard_starts_refresh_when_data_older_than_one_hour(api, repo):
    refresh_control.last_refresh["at"] = 0.0
    for action in repo.actions:
        action["maj_le"] = (NOW - timedelta(hours=2)).isoformat()
    before = len(repo.scores)
    body = api.get("/api/dashboard").json()
    assert body["actualisation"]["lancee_automatiquement"] is True
    assert len(repo.scores) == before + 5  # la tâche de fond a tourné (TestClient l'attend)
    again = api.get("/api/dashboard").json()  # moins de 2 minutes après : pas de nouvelle
    assert again["actualisation"]["lancee_automatiquement"] is False


def test_dashboard_does_not_refresh_fresh_data(api, repo):
    refresh_control.last_refresh["at"] = 0.0
    for action in repo.actions:
        action["maj_le"] = (NOW - timedelta(minutes=20)).isoformat()
    before = len(repo.scores)
    assert api.get("/api/dashboard").json()["actualisation"]["lancee_automatiquement"] is False
    assert len(repo.scores) == before


def test_is_stale():
    assert refresh_control.is_stale(None, NOW)
    assert refresh_control.is_stale((NOW - timedelta(minutes=61)).isoformat(), NOW)
    assert not refresh_control.is_stale((NOW - timedelta(minutes=59)).isoformat().replace("+00:00", "Z"), NOW)
    assert not refresh_control.is_stale("2026-11-25T16:30:00", NOW)  # sans fuseau : UTC


def test_dashboard_gives_small_weekly_change_precisely_with_euros(api, repo):
    repo.portfolio["val_semaine_prec"] = Decimal("500040.00")  # perte de 40 € sur la semaine
    body = api.get("/api/dashboard").json()
    assert body["variation_hebdo_eur"] == -40.0
    assert body["variation_hebdo_pct"] == pytest.approx(-0.008, abs=1e-4)


# --- Simulateur : un montant par action et un total (D-14) -------------------------------


def test_simulate_with_one_amount_per_stock_and_total(api, repo):
    set_price(repo, "DSY.PA", "34.80")
    set_price(repo, "AI.PA", "168.40")
    body = api.post("/api/simulate", json={"operation": "ACHAT", "operations": [
        {"ticker": "DSY.PA", "montant_eur": 50000}, {"ticker": "AI.PA", "montant_eur": 20000},
    ]}).json()
    dsy, ai = body["resultats"]
    assert (dsy["quantite_entiere"], dsy["montant_demande"]) == (1436, 50000)
    assert (ai["quantite_entiere"], ai["montant_reel_investi"]) == (118, 19871.20)
    assert dsy["cash_apres_operation"] == 450027.20
    assert ai["cash_apres_operation"] == 430156.00  # le cash est décompté ligne après ligne
    total = body["total"]
    assert total["montant_demande"] == 70000 and total["montant_reel"] == 69844.00
    assert total["reliquat"] == 156.00 and total["cash_apres"] == 430156.00
    assert total["dividende_annuel"] == 416.44 + ai["dividende_annuel_estime_eur"]
    assert body["avertissement"] is None


def test_simulate_total_above_cash_refuses_last_lines(api, repo):
    body = api.post("/api/simulate", json={"operation": "ACHAT", "operations": [
        {"ticker": "DSY.PA", "montant_eur": 300000}, {"ticker": "TTE.PA", "montant_eur": 300000},
    ]}).json()
    first, second = body["resultats"]
    assert first["verdict"] != "REFUSE" and second["verdict"] == "REFUSE"
    assert second["raisons"][0].startswith("Vous disposez de")
    assert body["total"]["nb_refusees"] == 1
    assert "dépasse votre cash" in body["avertissement"]


@pytest.mark.parametrize(
    "payload",
    [
        {"operation": "ACHAT", "operations": [{"ticker": "DSY.PA", "montant_eur": 0}]},
        {"operation": "ACHAT", "tickers": ["DSY.PA"]},  # ancien format sans montant
        {"operation": "ACHAT", "operations": []},
    ],
)
def test_simulate_per_stock_input_errors(api, payload):
    assert api.post("/api/simulate", json=payload).status_code == 422


def test_simulate_per_stock_unknown_ticker_is_404(api):
    response = api.post("/api/simulate", json={"operation": "ACHAT", "operations": [{"ticker": "ZZZ.PA", "montant_eur": 10}]})
    assert response.status_code == 404


# --- Profil de risque (D-17) -------------------------------------------------------------


def test_profile_lists_the_three_profiles_and_defaults(api):
    body = api.get("/api/profil").json()
    assert [p["id"] for p in body["profils"]] == ["prudent", "equilibre", "dynamique"]
    assert [(p["seuil_achat"], p["seuil_vente"]) for p in body["profils"]] == [(60, 40), (55, 45), (50, 40)]
    assert body["profil"] == {"id": None, "nom": "Par défaut", "seuil_achat": 60.0, "seuil_vente": 40.0, "a_choisir": True,
                              "part_max_action_pct": None, "exposition_avertissement_pct": 35.0}
    assert [p["part_max_action_pct"] for p in body["profils"]] == [10.0, 20.0, None]  # D-26
    assert body["enregistrable"] is True and set(body["notes"]) == set(config.TICKERS)


@pytest.mark.parametrize(("profil", "note", "attendu"), [
    ("prudent", 55.2, "RIEN"), ("equilibre", 55.2, "ACHAT"), ("dynamique", 50.0, "ACHAT"),
    ("dynamique", 45.0, "RIEN"), ("equilibre", 45.0, "VENTE"),
])
def test_choosing_a_profile_changes_advice_immediately(api, repo, profil, note, attendu):
    action_id = repo.action_by_ticker("TTE.PA")["id"]
    repo.latest_scores()[action_id]["score_global"] = note
    response = api.put("/api/profil", json={"profil": profil})
    assert response.status_code == 200 and repo.portfolio["profil_risque"] == profil
    conseil = api.get("/api/stocks/TTE.PA").json()["conseil"]
    assert conseil["decision"] == attendu
    achat, vente = config.thresholds_for(profil)
    assert (conseil["seuil_achat"], conseil["seuil_vente"]) == (achat, vente)
    dashboard = api.get("/api/dashboard").json()
    assert dashboard["profil"]["id"] == profil
    assert next(a for a in dashboard["actions"] if a["ticker"] == "TTE.PA")["conseil"] == attendu


def test_unknown_profile_is_422(api):
    assert api.put("/api/profil", json={"profil": "kamikaze"}).status_code == 422


def test_profile_not_saved_before_migration_005(api, repo):
    del repo.portfolio["profil_risque"]
    body = api.get("/api/profil").json()
    assert body["enregistrable"] is False
    response = api.put("/api/profil", json={"profil": "prudent"})
    assert response.status_code == 409 and "migration 005" in response.json()["detail"]


def test_first_connection_asks_for_profile_and_name(api, repo):
    """D-18 : sans profil choisi, le tableau de bord demande le dialogue de bienvenue."""
    assert api.get("/api/dashboard").json()["profil"]["a_choisir"] is True
    response = api.put("/api/profil", json={"profil": "equilibre", "nom_client": "  M.   Dupont "})
    assert response.status_code == 200
    assert repo.portfolio["nom_client"] == "M. Dupont" and repo.portfolio["profil_risque"] == "equilibre"
    body = api.get("/api/dashboard").json()
    assert body["profil"]["a_choisir"] is False and body["nom_client"] == "M. Dupont"


def test_blank_name_is_refused(api):
    assert api.put("/api/profil", json={"profil": "prudent", "nom_client": "   "}).status_code == 422


def test_logout_clears_name_and_profile_but_keeps_the_portfolio(api, repo):
    """D-20 : « Se déconnecter » ramène au dialogue de bienvenue sans toucher au portefeuille."""
    dsy = repo.action_by_ticker("DSY.PA")["id"]
    repo.execute_transaction(repo.portfolio["id"], dsy, "ACHAT", 10, {})
    api.put("/api/profil", json={"profil": "prudent", "nom_client": "M. Dupont"})
    cash = repo.portfolio["cash_disponible"]
    response = api.delete("/api/profil")
    assert response.status_code == 200 and "déconnecté" in response.json()["message"]
    assert repo.portfolio["profil_risque"] is None and repo.portfolio["nom_client"] is None
    assert repo.portfolio["cash_disponible"] == cash and len(repo.transactions) == 1
    assert api.get("/api/dashboard").json()["profil"]["a_choisir"] is True


def test_d24_chart_analysis_on_stock_page_and_simulator(api):
    analyse = api.get("/api/stocks/DSY.PA").json()["graphique"]["analyse"]
    assert analyse["lecture"] and len(analyse["moyennes"]) == 3
    assert all(s["niveau"] < analyse["cours"] for s in analyse["supports"])
    assert all(r["niveau"] > analyse["cours"] for r in analyse["resistances"])
    result = simulate(api)["resultats"][0]
    assert result["analyse_graphique"] and result["raisons"]  # raisons inchangées (2 à 4)


# --- D-26 : saisie en nombre d'actions et limite d'exposition par profil ----------------


def simulate_lines(api, lines, operation="ACHAT"):
    response = api.post("/api/simulate", json={"operations": lines, "operation": operation})
    assert response.status_code == 200, response.text
    return response.json()["resultats"]


def test_d26_buy_by_number_of_shares(api, repo):
    price = repo.action_by_ticker("DSY.PA")["dernier_cours"]
    result = simulate_lines(api, [{"ticker": "DSY.PA", "quantite": 12}])[0]
    assert result["quantite_entiere"] == 12 and result["unite"] == "actions"
    assert Decimal(str(result["montant_reel_investi"])) == (price * 12).quantize(Decimal("0.01"))
    assert Decimal(str(result["reliquat_cash"])) == 0


def test_d26_line_needs_exactly_one_unit(api):
    for line in ({"ticker": "DSY.PA"}, {"ticker": "DSY.PA", "quantite": 3, "montant_eur": 100}, {"ticker": "DSY.PA", "quantite": 0}):
        assert api.post("/api/simulate", json={"operations": [line], "operation": "ACHAT"}).status_code == 422


def test_d26_sell_more_shares_than_held_is_refused(api, repo):
    dsy = repo.action_by_ticker("DSY.PA")["id"]
    repo.execute_transaction(repo.portfolio["id"], dsy, "ACHAT", 10, {})
    result = simulate_lines(api, [{"ticker": "DSY.PA", "quantite": 11}], "VENTE")[0]
    assert result["verdict"] == "REFUSE" and "que 10 actions" in result["motif_refus"]
    assert simulate_lines(api, [{"ticker": "DSY.PA", "quantite": 10}], "VENTE")[0]["quantite_entiere"] == 10


def test_d26_prudent_profile_blocks_more_than_10_pct_on_one_stock(api, repo):
    api.put("/api/profil", json={"profil": "prudent"})
    over = simulate_lines(api, [{"ticker": "AI.PA", "montant_eur": 60000}])[0]  # 12 % de 500 000 €
    assert over["verdict"] == "REFUSE" and "10 %" in over["motif_refus"] and over["quantite_entiere"] == 0
    ok = simulate_lines(api, [{"ticker": "AI.PA", "montant_eur": 45000}])[0]
    assert ok["verdict"] != "REFUSE" and ok["exposition"]["apres_pct"] <= 10
    # La position déjà détenue compte : on ne contourne pas la limite en achetant en deux fois.
    ai = repo.action_by_ticker("AI.PA")
    repo.execute_transaction(repo.portfolio["id"], ai["id"], "ACHAT", int(45000 / ai["dernier_cours"]), {})
    again = simulate_lines(api, [{"ticker": "AI.PA", "montant_eur": 10000}])[0]
    assert again["verdict"] == "REFUSE" and "déjà" in again["motif_refus"]


def test_d26_limit_enforced_when_recording(api, repo):
    api.put("/api/profil", json={"profil": "equilibre"})
    ai = repo.action_by_ticker("AI.PA")
    quantity = int(Decimal(150000) / ai["dernier_cours"])  # 30 % > 20 %
    response = api.post("/api/transactions", json={
        "ticker": "AI.PA", "operation": "ACHAT", "quantite": quantity,
        "cours_simule": str(ai["dernier_cours"]), "date_conseil": NOW.isoformat()})
    assert response.status_code == 400 and "20 %" in response.json()["detail"]
    assert repo.get_transactions(repo.portfolio["id"]) == []


def test_d26_dynamic_profile_is_free_but_warned(api):
    api.put("/api/profil", json={"profil": "dynamique"})
    result = simulate_lines(api, [{"ticker": "AI.PA", "montant_eur": 200000}])[0]  # 40 %
    assert result["verdict"] != "REFUSE"
    assert result["exposition"]["max_pct"] is None and "40" in result["exposition"]["avertissement"]
    small = simulate_lines(api, [{"ticker": "AI.PA", "montant_eur": 20000}])[0]
    assert small["exposition"]["avertissement"] is None
