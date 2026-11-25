"""Réglages : RG-04 et valeurs de la SPEC (§3 à §11)."""

from decimal import Decimal

import pytest

import config
from config import ConfigError, check_rg04


def test_rg04_info_weight_strictly_highest():
    poids = config.POIDS
    assert all(poids["infos"] > p for nom, p in poids.items() if nom != "infos")
    check_rg04(poids)  # ne lève rien


def test_weights_match_spec_7_1():
    assert dict(config.POIDS) == {"infos": 0.40, "tech": 0.25, "ratios": 0.25, "hasard": 0.10}
    assert sum(config.POIDS.values()) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "poids",
    [
        {"infos": 0.30, "tech": 0.40, "ratios": 0.20, "hasard": 0.10},  # infos dépassé
        {"infos": 0.40, "tech": 0.40, "ratios": 0.10, "hasard": 0.10},  # égalité (V8)
        {"infos": 0.50, "tech": 0.25, "ratios": 0.25, "hasard": 0.10},  # somme ≠ 1
        {"infos": 0.60, "tech": 0.30, "ratios": 0.20, "hasard": -0.10},  # poids négatif
        {"infos": 0.50, "tech": 0.25, "ratios": 0.25},  # pilier manquant
    ],
)
def test_rg04_rejects_invalid_weights(poids):
    with pytest.raises(ConfigError):
        check_rg04(poids)


def test_decision_and_alert_thresholds_match_spec():
    assert (config.SEUIL_ACHAT, config.SEUIL_VENTE) == (60.0, 40.0)  # SPEC §7.2
    assert (config.ALERTE_APPROCHE_PCT, config.ALERTE_ATTEINT_PCT) == (-7.0, -10.0)  # SPEC §11.2


def test_pillar_parameters_match_spec():
    assert dict(config.IMPORTANCES_TECH) == {"bollinger": 9, "rsi": 7, "macd": 6, "mm": 5, "tendance": 5}
    assert dict(config.IMPORTANCES_RATIOS) == {"ca": 7, "dpa": 6, "rendement": 6}
    assert (config.INFO_DEMI_VIE_JOURS, config.INFO_FENETRE_JOURS) == (2.0, 7)
    assert (config.MACD_RAPIDE, config.MACD_LENTE, config.MACD_SIGNAL) == (12, 26, 9)
    assert config.MM_PERIODES == (20, 50, 200)


def test_money_constants_are_decimal():
    assert config.CAPITAL_INITIAL == Decimal("500000.00")
    assert isinstance(config.FRAIS_PCT, Decimal)


def test_five_tickers_of_the_scope():
    assert set(config.TICKERS) == {"DSY.PA", "TTE.PA", "CAP.PA", "RMS.PA", "AI.PA"}


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("SEUIL_ACHAT", 45.0),  # seuil d'achat sous le neutre
        ("ALERTE_APPROCHE_PCT", -12.0),  # approche plus loin que atteint
        ("RAISONS_MIN", 5),  # plus que le maximum
    ],
)
def test_check_config_rejects_inconsistent_thresholds(monkeypatch, name, value):
    monkeypatch.setattr(config, name, value)
    with pytest.raises(ConfigError):
        config.check_config()


def test_settings_never_show_secret_keys(monkeypatch):
    monkeypatch.setenv("SUPABASE_KEY", "sb_secret_ne_doit_pas_apparaitre")
    monkeypatch.setenv("NEWS_API_KEY", "news_ne_doit_pas_apparaitre")
    text = repr(config.load_settings())
    assert "ne_doit_pas_apparaitre" not in text


def test_cors_origins_are_parsed(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " http://localhost:5173 , https://pf500.vercel.app/ ,")
    assert config.load_settings().cors_origins == ("http://localhost:5173", "https://pf500.vercel.app")
