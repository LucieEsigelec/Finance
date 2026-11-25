"""Cas de vérification V1 à V16 de la SPEC §12.1 : l'application doit retrouver
exactement les résultats chiffrés des exemples du dossier de spécification.

V14 (validation alors que le cash ne suffit plus) se vérifie sur la route
POST /api/transactions : voir tests/test_routes.py.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

import config
import main
from config import ConfigError
from services.common import round_half_up
from services.decision_engine import (
    ACHAT,
    APPROCHE,
    ATTEINT,
    AUCUN,
    NE_RIEN_FAIRE,
    REFUSE,
    RIEN,
    VALIDER,
    VENTE,
    alert_level,
    decide,
    final_score,
    simulate_operation,
)
from services.info_scoring import NO_RECENT_NEWS, InfoScoringService
from services.randomness_service import RandomnessService
from services.ratio_scoring import RatioScoringService
from services.technical_scoring import bollinger_signal, rsi_signal, tech_score
from tools.stress_test import shocked_level

NOW = datetime(2026, 11, 25, 18, 0, tzinfo=timezone.utc)
SPEC_NOTES = {"infos": 66.9, "tech": 60.1, "ratios": 57.4, "hasard": 37.2}


def test_v01_bollinger_96_in_95_105_gives_plus_0_8():
    assert bollinger_signal(96, 95, 105) == pytest.approx(0.8)


def test_v02_rsi_35_gives_plus_0_75():
    assert rsi_signal(35) == pytest.approx(0.75)


def test_v03_five_signals_give_tech_score_60_1():
    signals = {"bollinger": 0.8, "rsi": 0.75, "macd": -0.5, "mm": -0.4, "tendance": -0.2}
    assert round_half_up(tech_score(signals), 1) == 60.1


def test_v04_articles_80_yesterday_and_30_four_days_ago_give_66_9():
    articles = [
        {"titre": "Nouveaux contrats", "date_pub": NOW - timedelta(days=1), "score_impact": 80},
        {"titre": "Objectif abaissé", "date_pub": NOW - timedelta(days=4), "score_impact": 30},
    ]
    result = InfoScoringService().score(articles, NOW)
    assert round_half_up(result.score, 1) == 66.9
    assert round_half_up(result.impact_points, 1) == 6.8  # SPEC §4.2
    assert result.faits_cles[0]["titre"] == "Nouveaux contrats"


def test_v05_no_article_in_7_days_gives_50_and_message():
    old = [{"titre": "Ancien", "date_pub": NOW - timedelta(days=8), "score_impact": 90}]
    result = InfoScoringService().score(old, NOW)
    assert result.score == 50
    assert result.message == NO_RECENT_NEWS == "aucune actualité récente"


def test_v06_section_5_example_gives_ratio_score_57_4():
    result = RatioScoringService().score(
        ca=107, ca_precedent=100, dpa=1.08, dpa_precedent=1.00, rendement=0.8, moyenne_rendement=2.6
    )
    assert result.criteres == pytest.approx({"ca": 0.4, "dpa": 1.0, "rendement": -1.0})
    assert round_half_up(result.score, 1) == 57.4


def test_v07_same_stock_same_week_gives_same_random_score():
    service = RandomnessService()
    monday, friday = datetime(2026, 11, 23).date(), datetime(2026, 11, 27).date()
    first, second = service.score("DSY.PA", monday), service.score("DSY.PA", friday)
    assert first == second
    assert 0 <= first.score <= 100
    assert service.score("DSY.PA", datetime(2026, 11, 30).date()).seed != first.seed


def test_v08_info_weight_equal_to_tech_weight_refuses_to_start(monkeypatch):
    """V8 : poids Informations égal au poids Graphique → l'application refuse de démarrer."""
    monkeypatch.setattr(
        config, "POIDS", {"infos": 0.30, "tech": 0.30, "ratios": 0.30, "hasard": 0.10}
    )
    with pytest.raises(ConfigError, match="RG-04"):
        main.create_app()


def test_v09_spec_notes_give_59_9_and_rien():
    note = final_score(SPEC_NOTES)
    assert round_half_up(note, 1) == 59.9
    assert decide(note) == RIEN


def test_v10_same_notes_with_random_50_give_61_1_and_achat():
    note = final_score({**SPEC_NOTES, "hasard": 50})
    assert round_half_up(note, 1) == 61.1
    assert decide(note) == ACHAT


def test_v11_buy_50000_at_34_80():
    op = simulate_operation(
        ACHAT, Decimal("50000"), Decimal("34.80"), Decimal("500000"), 0, ACHAT, AUCUN, Decimal("0.29")
    )
    assert op.quantite == 1436
    assert op.montant_reel == Decimal("49972.80")
    assert op.reliquat == Decimal("27.20")
    assert op.dividende == Decimal("416.44")
    assert op.verdict == VALIDER


def test_v12_sell_10000_at_36_with_1436_held():
    op = simulate_operation(
        VENTE, Decimal("10000"), Decimal("36"), Decimal("450027.20"), 1436, VENTE, AUCUN, Decimal("0.29")
    )
    assert op.quantite == 277
    assert op.montant_reel == Decimal("9972.00")


def test_v13_buy_600000_with_500000_cash_is_refused():
    op = simulate_operation(
        ACHAT, Decimal("600000"), Decimal("34.80"), Decimal("500000"), 0, ACHAT, AUCUN, Decimal("0.29")
    )
    assert op.verdict == REFUSE
    assert op.quantite == 0
    assert "500 000,00 €" in op.motif_refus


def test_v15_simulated_drop_of_12_5_pct_triggers_red_alert():
    cash, held, prices = Decimal("100000"), {"DSY.PA": 10000}, {"DSY.PA": Decimal("40")}
    variation, level = shocked_level(cash, held, prices, Decimal("500000"), 12.5)
    assert variation == pytest.approx(-10.0)
    assert level == ATTEINT
    assert shocked_level(cash, held, prices, Decimal("500000"), 12.4)[1] == APPROCHE


def test_v16_minus_8_pct_and_buy_request_on_achat_stock_gives_do_nothing():
    level = alert_level(-8.0)
    assert level == APPROCHE
    op = simulate_operation(
        ACHAT, Decimal("10000"), Decimal("34.80"), Decimal("400000"), 0, ACHAT, level, Decimal("0.29")
    )
    assert op.verdict == NE_RIEN_FAIRE
