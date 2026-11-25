"""Services de calcul : règles complémentaires aux cas V1–V16 (SPEC §3 à §11)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

import config
from services import sentiment
from services.common import note_from_signal, round_half_up, weighted_mean
from services.decision_engine import (
    ACHAT,
    APPROCHE,
    ATTEINT,
    AUCUN,
    CONSERVER,
    NE_RIEN_FAIRE,
    PRIVILEGIER_VENTE,
    REFUSE,
    RIEN,
    VALIDER,
    VENTE,
    alert_level,
    build_reasons,
    confidence,
    decide,
    fmt_eur,
    fmt_pct,
    forecast,
    forecast_euros,
    portfolio_value,
    positions,
    realized_gains,
    simulate_operation,
    verdict,
    weekly_returns,
)
from services.info_scoring import InfoScoringService, article_weight, impact_score
from services.ratio_scoring import RatioScoringService, ca_signal, dpa_signal, estimated_dividend
from services.technical_scoring import (
    TechnicalScoringService,
    compute_indicators,
    macd_signal,
    mm_signal,
    trend_signal,
)

NOW = datetime(2026, 11, 25, 18, 0, tzinfo=timezone.utc)


def make_history(n=300, start=100.0, drift=0.001, seed=1, end=date(2026, 11, 25)):
    rng = np.random.default_rng(seed)
    closes = start * np.cumprod(1 + drift + rng.normal(0, 0.01, n))
    days = pd.bdate_range(end=end, periods=n)
    return pd.DataFrame(
        {"date_seance": days.date, "open": closes, "high": closes * 1.01, "low": closes * 0.99, "close": closes}
    )


# --- Échelle commune ---------------------------------------------------------------


def test_note_scale_examples_spec_1_2():
    assert note_from_signal(1) == 100
    assert note_from_signal(0) == 50
    assert note_from_signal(-0.4) == pytest.approx(30)
    assert note_from_signal(3) == 100  # borné


def test_weighted_mean_ignores_missing_values():
    assert weighted_mean({"a": 1.0, "b": None}, {"a": 1, "b": 5}) == 1.0
    assert weighted_mean({"a": None}, {"a": 1}) is None


def test_round_half_up_is_school_rounding():
    assert round_half_up(59.855, 1) == 59.9
    assert round_half_up(0.25, 1) == 0.3


# --- Analyse graphique -------------------------------------------------------------


def test_macd_cross_and_hold_signals():
    up_cross = pd.Series([-1, -1, -1, -1, -1, 1.0]), pd.Series([0.0] * 6)
    assert macd_signal(*up_cross) == 1.0
    stays_above = pd.Series([1.0] * 10), pd.Series([0.0] * 10)
    assert macd_signal(*stays_above) == 0.5
    stays_below = pd.Series([-1.0] * 10), pd.Series([0.0] * 10)
    assert macd_signal(*stays_below) == -0.5


def test_mm_signal_weights_close_vs_mm20_double():
    # cours 2 % au-dessus de MM20 (+1), MM20 = MM50 (0), MM50 5 % sous MM200 (−1)
    assert mm_signal(102, 100, 100, 100 / 0.95) == pytest.approx((2 * 1 + 0 - 1) / 4, abs=1e-3)
    # MM200 manquante (historique court) : ignorée
    assert mm_signal(102, 100, 100, float("nan")) == pytest.approx(2 / 3)


def test_trend_signal_is_clipped():
    assert trend_signal(1.5) == 0.5
    assert trend_signal(-9) == -1


def test_technical_service_uses_no_data_after_date_calcul():
    history = make_history()
    cutoff = date(2026, 10, 1)
    future_spike = history.copy()
    future_spike.loc[pd.to_datetime(future_spike["date_seance"]).dt.date > cutoff, "close"] *= 3
    service = TechnicalScoringService()
    assert service.score(history, cutoff).score == service.score(future_spike, cutoff).score


def test_technical_service_short_history_ignores_mm200():
    result = TechnicalScoringService().score(make_history(n=60), date(2026, 11, 25))
    assert 0 <= result.score <= 100
    assert result.signaux["bollinger"] is not None


def test_technical_service_without_history_is_neutral():
    empty = make_history().iloc[0:0]
    assert TechnicalScoringService().score(empty, date(2026, 11, 25)).score == 50


def test_compute_indicators_columns():
    df = compute_indicators(make_history())
    for col in ("mm20", "mm50", "mm200", "boll_haut", "boll_bas", "rsi", "macd", "macd_signal", "macd_hist"):
        assert col in df.columns
    assert df["mm200"].iloc[:199].isna().all() and not np.isnan(df["mm200"].iloc[-1])


# --- Informations ------------------------------------------------------------------


def test_article_weight_table_spec_4_1():
    assert [round(article_weight(d), 2) for d in (0, 1, 2, 4, 7)] == [1, 0.71, 0.5, 0.25, 0.09]
    assert article_weight(7.5) == 0 and article_weight(-0.1) == 0


def test_impact_score_announcement_counts_double():
    assert impact_score(0.6, True) == 80
    assert impact_score(0.6, False) == 65


def test_info_service_ignores_articles_after_date_calcul():
    articles = [{"titre": "Futur", "date_pub": NOW + timedelta(hours=1), "score_impact": 100}]
    assert InfoScoringService().score(articles, NOW).score == 50


def test_sentiment_lexicon_french_and_english():
    assert sentiment.sentiment("Dassault Systèmes annonce de nouveaux contrats, le titre en hausse") > 0
    assert sentiment.sentiment("Avertissement sur les résultats : l'action chute") < 0
    assert sentiment.sentiment("Capgemini shares jump after strong results") > 0
    assert sentiment.sentiment("pas de hausse attendue") < 0  # négation
    assert sentiment.sentiment("Assemblée générale le 12 mai") == 0
    assert sentiment.is_announcement("Hermès publie ses résultats annuels")
    assert not sentiment.is_announcement("Le luxe reprend des couleurs")


# --- Ratios ------------------------------------------------------------------------


def test_ratio_signals_piecewise():
    assert ca_signal(10) == 1 and ca_signal(5) == 0 and ca_signal(0) == -1 and ca_signal(-3) == -1
    assert dpa_signal(8) == 1 and dpa_signal(0.5) == 0 and dpa_signal(-5) == -1


def test_ratio_missing_data_is_neutral():
    assert RatioScoringService().score(None, None, None, None, None, None).score == 50


def test_estimated_dividend_is_decimal_to_the_cent():
    assert estimated_dividend(1436, 0.29) == Decimal("416.44")
    assert estimated_dividend(10, None) == Decimal("0.00")


# --- Décision ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("note", "conseil"), [(60, ACHAT), (59.94, RIEN), (59.95, ACHAT), (40, VENTE), (40.06, RIEN), (50, RIEN)]
)
def test_decision_thresholds_spec_7_2(note, conseil):
    assert decide(note) == conseil


def test_confidence_levels():
    assert confidence(61.1) == "faible"
    assert confidence(32) == "moyenne"
    assert confidence(80) == "forte"


def test_forecast_spec_9_example_shape():
    returns = pd.Series([0.2 + 2.5 * (1 if i % 2 else -1) for i in range(52)])
    result = forecast(returns, 59.9)
    assert result["favorable"] - result["central"] == pytest.approx(result["sigma"], abs=0.01)
    assert result["central"] > result["mu"]  # note > 50 décale vers le haut
    assert forecast(returns.iloc[:20], 59.9) is None  # < 6 mois


def test_forecast_euros_spec_9_example():
    scenarios = {"defavorable": -1.8, "central": 0.7, "favorable": 3.2}
    assert forecast_euros(scenarios, Decimal("49972.80")) == {
        "defavorable": -900, "central": 350, "favorable": 1599
    }
    assert forecast_euros(None, Decimal(1)) is None


def test_weekly_returns_from_daily_history():
    returns = weekly_returns(make_history(n=300))
    assert 55 <= len(returns) <= 62


@pytest.mark.parametrize(
    ("operation", "conseil", "alerte", "attendu"),
    [
        (ACHAT, ACHAT, AUCUN, VALIDER),
        (ACHAT, RIEN, AUCUN, NE_RIEN_FAIRE),
        (ACHAT, VENTE, AUCUN, PRIVILEGIER_VENTE),
        (VENTE, VENTE, AUCUN, VALIDER),
        (VENTE, RIEN, AUCUN, NE_RIEN_FAIRE),
        (VENTE, ACHAT, AUCUN, CONSERVER),
        (ACHAT, ACHAT, ATTEINT, NE_RIEN_FAIRE),
        (VENTE, RIEN, ATTEINT, VALIDER),
        (VENTE, ACHAT, APPROCHE, CONSERVER),
    ],
)
def test_verdict_table_spec_10_3(operation, conseil, alerte, attendu):
    assert verdict(operation, conseil, alerte) == attendu


def test_simulation_refusals():
    too_small = simulate_operation(ACHAT, Decimal("10"), Decimal("34.80"), Decimal("1000"), 0, ACHAT, AUCUN, 0.29)
    assert too_small.verdict == REFUSE and "une seule action" in too_small.motif_refus
    not_held = simulate_operation(VENTE, Decimal("1000"), Decimal("34.80"), Decimal("0"), 0, VENTE, AUCUN, 0.29)
    assert not_held.verdict == REFUSE and "découvert" in not_held.motif_refus
    capped = simulate_operation(VENTE, Decimal("100000"), Decimal("10"), Decimal("0"), 50, VENTE, AUCUN, 0.29)
    assert capped.quantite == 50  # jamais plus que la position (RG-05)
    tiny_sale = simulate_operation(VENTE, Decimal("5"), Decimal("10"), Decimal("0"), 50, VENTE, AUCUN, 0.29)
    assert tiny_sale.verdict == REFUSE


def test_alert_levels_boundaries():
    assert alert_level(-6.99) == AUCUN
    assert alert_level(-7.0) == APPROCHE
    assert alert_level(-9.99) == APPROCHE
    assert alert_level(-10.0) == ATTEINT


def test_positions_value_and_realized_gains_history_example():
    txs = [
        {"id": "1", "ticker": "CAP.PA", "type_op": ACHAT, "quantite_entiere": 300, "prix_unitaire": 140.10,
         "date_execution": "2026-11-04T11:18:00"},
        {"id": "2", "ticker": "CAP.PA", "type_op": VENTE, "quantite_entiere": 300, "prix_unitaire": 146.20,
         "date_execution": "2026-11-12T09:31:00"},
        {"id": "3", "ticker": "DSY.PA", "type_op": ACHAT, "quantite_entiere": 1436, "prix_unitaire": 34.80,
         "date_execution": "2026-11-18T14:05:00"},
    ]
    assert positions(txs) == {"DSY.PA": 1436}
    assert realized_gains(txs) == {"2": Decimal("1830.00")}  # maquette Historique
    value = portfolio_value(Decimal("450027.20"), {"DSY.PA": 1436}, {"DSY.PA": Decimal("35.62")})
    assert value == Decimal("501177.52")


def test_french_formats():
    assert fmt_eur(Decimal("49972.8")) == "49 972,80 €"
    assert fmt_pct(-1.84) == "−1,8 %"
    assert fmt_pct(3.2) == "+3,2 %"


# --- Raisons (RG-03) ----------------------------------------------------------------

TECH = {"bollinger": 0.8, "rsi": 0.75, "macd": -0.5, "mm": -0.4, "tendance": -0.2}
FAITS = [{"titre": "Nouveaux contrats industriels bien accueillis", "score_impact": 80}]


def ratios_example():
    return RatioScoringService().score(107, 100, 1.08, 1.0, 0.8, 2.6)


def test_reasons_example_8_2_rien_59_9():
    notes = {"infos": 66.9, "tech": 60.1, "ratios": 57.4, "hasard": 37.2}
    reasons = build_reasons(59.855, RIEN, notes, TECH, FAITS, ratios_example())
    assert config.RAISONS_MIN <= len(reasons) <= config.RAISONS_MAX
    assert reasons[0].startswith("Note de 59,9, juste sous le seuil d'achat (60)")
    assert reasons[1] == "Informations (poids majoritaire) : Nouveaux contrats industriels bien accueillis."
    assert "proche du bas de sa fourchette" in reasons[2]
    assert not any("hasard" in r.lower() for r in reasons)


def test_reasons_alert_comes_first_and_vente():
    notes = {"infos": 20, "tech": 30, "ratios": 45, "hasard": 50}
    faits = [{"titre": "Avertissement sur les résultats", "score_impact": 15}]
    tech = {"bollinger": -0.9, "rsi": -0.8, "macd": -1, "mm": -0.5, "tendance": -1}
    reasons = build_reasons(30, VENTE, notes, tech, faits, None, ATTEINT, -10.4)
    assert reasons[0].startswith("Limite de perte atteinte : −10,4 %")
    assert "Avertissement sur les résultats" in reasons[1]
    assert len(reasons) <= 4


def test_reasons_never_fewer_than_two():
    notes = {"infos": 50, "tech": 50, "ratios": 50, "hasard": 50}
    signals = dict.fromkeys(TECH)
    reasons = build_reasons(50, RIEN, notes, signals, [], None, info_message="aucune actualité récente")
    assert len(reasons) == 2
    assert reasons[1] == "Informations : aucune actualité récente."


def test_reasons_vigilance_from_opposing_pillar():
    notes = {"infos": 80, "tech": 70, "ratios": 30, "hasard": 50}
    reasons = build_reasons(64, ACHAT, notes, TECH, FAITS, ratios_example())
    assert any(r.startswith("Point de vigilance") for r in reasons)


def test_ratio_phrase_for_weak_but_positive_growth_is_not_called_a_rise():
    weak = RatioScoringService().score(101.7, 100, None, None, None, None)
    reasons = build_reasons(45, RIEN, {"infos": 50, "tech": 50, "ratios": weak.score, "hasard": 50},
                            {}, [], weak)
    assert any("croissance du chiffre d'affaires faible (+1,7 % sur un an)" in r for r in reasons)


def test_sentiment_new_words():
    assert sentiment.sentiment("L'action Dassault Systèmes enfonce son support et cède 8,5 %") < 0
    assert sentiment.sentiment("L'action Air Liquide grappille 0,2 %") > 0
