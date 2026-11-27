"""Lecture détaillée du graphique (D-24) : moyennes, croisements, supports / résistances."""

from datetime import date, timedelta

import pandas as pd

from services.chart_analysis import analyze_chart, cluster_levels, recent_cross, support_resistance

START = date(2025, 1, 1)


def frame(closes, spread=0.5):
    days = [START + timedelta(days=i) for i in range(len(closes))]
    return pd.DataFrame({
        "date_seance": days, "open": closes, "close": closes,
        "high": [c + spread for c in closes], "low": [c - spread for c in closes], "volume": 0,
    })


def zigzag(n_cycles=6, low=100.0, high=110.0, step=1.0):
    """Le cours oscille entre ~100 et ~110 : un support et une résistance nets."""
    up = [low + step * i for i in range(int((high - low) / step) + 1)]
    cycle = up + up[-2:0:-1]
    return [c for _ in range(n_cycles) for c in cycle]


def test_cluster_groups_close_prices():
    levels = cluster_levels([100.0, 100.8, 110.0, 110.5, 125.0], 1.5)
    assert [(lv["niveau"], lv["touches"]) for lv in levels] == [(100.4, 2), (110.25, 2), (125.0, 1)]


def test_zigzag_gives_support_and_resistance():
    closes = zigzag() + [100 + i for i in range(6)]  # remonte vers 105
    df = frame(closes)
    supports, resistances = support_resistance(df, closes[-1])
    assert supports and abs(supports[0]["niveau"] - 99.5) < 1 and supports[0]["touches"] >= 2
    assert resistances and abs(resistances[0]["niveau"] - 110.5) < 1 and resistances[0]["touches"] >= 2
    assert supports[0]["ecart_pct"] < 0 < resistances[0]["ecart_pct"]


def test_new_high_has_no_pivot_resistance_and_says_so():
    closes = [100 + 0.3 * i for i in range(260)]  # hausse régulière : plus haut historique
    result = analyze_chart(frame(closes, spread=0.0), START + timedelta(days=259))
    assert result["resistances"] == []
    assert any("plus haut de 6 mois" in s for s in result["lecture"])
    assert "trois moyennes" in result["lecture"][0] and "haussière" in result["lecture"][0]
    assert any("rangées à la hausse" in s for s in result["lecture"])


def test_golden_cross_detected():
    closes = [200 - 0.5 * i for i in range(200)] + [100 + 2.0 * i for i in range(60)]
    df = frame(closes)
    from services.technical_scoring import compute_indicators

    cross = recent_cross(compute_indicators(df), "mm50", "mm200", 60)
    assert cross and cross["sens"] == "hausse"


def test_no_data_after_calculation_date():
    closes = zigzag() + [100 + i for i in range(6)]
    df = frame(closes)
    day = df["date_seance"].iloc[-1]
    later = pd.concat([df, frame([500.0] * 10).assign(date_seance=[day + timedelta(days=i + 1) for i in range(10)])])
    assert analyze_chart(later, day) == analyze_chart(df, day)


def test_empty_history():
    assert analyze_chart(pd.DataFrame(columns=["date_seance", "close"]), date(2026, 1, 1)) is None


def test_sentences_are_plain_french():
    """ENF-01 : jamais un indicateur brut (« MM50 = … ») ; montants au format français."""
    result = analyze_chart(frame(zigzag() + [100 + i for i in range(6)]), START + timedelta(days=200))
    text = " ".join(result["lecture"])
    assert "MM" not in text and "=" not in text and "€" in text
