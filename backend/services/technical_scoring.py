"""Pilier 2 — Analyse graphique (TechnicalScoringService) — SPEC §3.

En bref : à partir des cours de clôture (table ``historique_cours``), on calcule
nous-mêmes 5 indicateurs avec la bibliothèque ``ta``. Chacun donne un signal entre
−1 (vendre) et +1 (acheter) :

- Bollinger : le cours est-il en bas (+1) ou en haut (−1) de son « couloir » de 20 jours ?
- RSI : le titre a-t-il trop baissé (RSI ≤ 30 → +1) ou trop monté (RSI ≥ 70 → −1) ?
- MACD : la moyenne courte vient-elle de passer au-dessus (+1) ou en dessous (−1) de la longue ?
- Moyennes mobiles : le cours et les moyennes courtes sont-ils au-dessus des longues ?
- Tendance : le cours monte-t-il (+3 %/semaine → +1) ou baisse-t-il sur un mois ?

La note du pilier est la moyenne des 5 signaux pondérée par leur importance
(9, 7, 6, 5, 5), ramenée sur 100. Un indicateur incalculable (historique trop court)
est ignoré. Aucun cours postérieur à la date de calcul n'est utilisé.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands

import config
from services.common import clip, is_missing, note_from_signal, weighted_mean

# ---------------------------------------------------------------------------
# Signaux élémentaires (SPEC §3.3) — chacun testé par les cas V1, V2…
# ---------------------------------------------------------------------------


def bollinger_signal(close: float, lower: float, upper: float) -> float | None:
    """position = (cours − bas) / (haut − bas) ; signal = 1 − 2 × position."""
    if any(is_missing(v) for v in (close, lower, upper)) or upper <= lower:
        return None
    position = (close - lower) / (upper - lower)
    return clip(1 - 2 * position)


def rsi_signal(rsi: float) -> float | None:
    """signal = (50 − RSI) / 20, borné : RSI 30 → +1, 50 → 0, 70 → −1."""
    if is_missing(rsi):
        return None
    return clip((config.RSI_CENTRE - rsi) / config.RSI_ECHELLE)


def macd_signal(macd: pd.Series, signal: pd.Series) -> float | None:
    """+1 / −1 si le MACD vient de croiser sa ligne de signal (fenêtre de 5 séances),
    +0,5 / −0,5 s'il reste au-dessus / en dessous."""
    diff = (macd - signal).dropna()
    if diff.empty:
        return None
    above = diff.iloc[-1] > 0
    window = diff.iloc[-(config.MACD_FENETRE_CROISEMENT_SEANCES + 1):]
    signs = np.sign(window.to_numpy())
    crossed = len(signs) > 1 and np.any(signs[:-1] != signs[-1])
    if crossed:
        return config.MACD_SIGNAL_CROISEMENT if above else -config.MACD_SIGNAL_CROISEMENT
    return config.MACD_SIGNAL_MAINTIEN if above else -config.MACD_SIGNAL_MAINTIEN


def _comparison(value: float, reference: float, ecart_pct: float) -> float | None:
    if is_missing(value) or is_missing(reference) or reference == 0:
        return None
    return clip((value / reference - 1) * 100 / ecart_pct)


def mm_signal(close: float, mm20: float, mm50: float, mm200: float) -> float | None:
    """signal = (2 × [cours/MM20] + [MM20/MM50] + [MM50/MM200]) / 4,
    chaque comparaison valant +1 à +2 %, +3 %, +5 % au-dessus (et −1 symétriquement)."""
    e1, e2, e3 = config.MM_ECARTS_PCT
    c1, c2, c3 = config.MM_COEFFICIENTS
    comparisons = {
        "c1": _comparison(close, mm20, e1),
        "c2": _comparison(mm20, mm50, e2),
        "c3": _comparison(mm50, mm200, e3),
    }
    return weighted_mean(comparisons, {"c1": c1, "c2": c2, "c3": c3})


def trend_pct_per_week(closes: pd.Series) -> float | None:
    """Pente de la droite des moindres carrés sur les 20 derniers cours, en % du cours
    moyen par semaine (5 séances)."""
    last = closes.dropna().iloc[-config.TENDANCE_JOURS:]
    if len(last) < config.TENDANCE_JOURS:
        return None
    slope = np.polyfit(np.arange(len(last)), last.to_numpy(dtype=float), 1)[0]
    return slope / float(last.mean()) * 100 * 5


def trend_signal(pct_per_week: float | None) -> float | None:
    if is_missing(pct_per_week):
        return None
    return clip(pct_per_week / config.TENDANCE_PCT_HEBDO_MAX)


def tech_score(signals: dict[str, float | None]) -> float:
    """note graphique = 50 + 50 × moyenne des signaux pondérée par leur importance."""
    mean = weighted_mean(signals, config.IMPORTANCES_TECH)
    return config.NOTE_NEUTRE if mean is None else note_from_signal(mean)


# ---------------------------------------------------------------------------
# Indicateurs complets (pour le score et pour les graphiques de la fiche action)
# ---------------------------------------------------------------------------


def compute_indicators(history: pd.DataFrame) -> pd.DataFrame:
    """Ajoute aux cours (colonnes date_seance, open, high, low, close) les colonnes
    mm20, mm50, mm200, boll_haut, boll_milieu, boll_bas, rsi, macd, macd_signal, macd_hist."""
    df = history.sort_values("date_seance").reset_index(drop=True).copy()
    close = df["close"].astype(float)
    for period in config.MM_PERIODES:
        df[f"mm{period}"] = close.rolling(period, min_periods=period).mean()
    bands = BollingerBands(close, window=config.BOLLINGER_PERIODE, window_dev=config.BOLLINGER_ECARTS_TYPES)
    df["boll_haut"] = bands.bollinger_hband()
    df["boll_milieu"] = bands.bollinger_mavg()
    df["boll_bas"] = bands.bollinger_lband()
    df["rsi"] = RSIIndicator(close, window=config.RSI_PERIODE).rsi()
    macd = MACD(
        close,
        window_slow=config.MACD_LENTE,
        window_fast=config.MACD_RAPIDE,
        window_sign=config.MACD_SIGNAL,
    )
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["macd_hist"] = macd.macd_diff()
    return df


@dataclass
class TechResult:
    score: float
    signaux: dict[str, float | None]
    details: dict[str, float | None] = field(default_factory=dict)


class TechnicalScoringService:
    """Lit un historique de cours et rend score_tech et signaux (DCT §5.2)."""

    def score(self, history: pd.DataFrame, date_calcul: date) -> TechResult:
        past = history[pd.to_datetime(history["date_seance"]).dt.date <= date_calcul]
        if past.empty:
            return TechResult(config.NOTE_NEUTRE, dict.fromkeys(config.IMPORTANCES_TECH))
        df = compute_indicators(past)
        last = df.iloc[-1]
        trend = trend_pct_per_week(df["close"].astype(float))
        signals = {
            "bollinger": bollinger_signal(last["close"], last["boll_bas"], last["boll_haut"]),
            "rsi": rsi_signal(last["rsi"]),
            "macd": macd_signal(df["macd"], df["macd_signal"]),
            "mm": mm_signal(last["close"], last["mm20"], last["mm50"], last["mm200"]),
            "tendance": trend_signal(trend),
        }
        details = {
            "rsi": None if is_missing(last["rsi"]) else float(last["rsi"]),
            "tendance_pct_semaine": trend,
            "cours": float(last["close"]),
            "mm20": None if is_missing(last["mm20"]) else float(last["mm20"]),
            "mm50": None if is_missing(last["mm50"]) else float(last["mm50"]),
        }
        return TechResult(tech_score(signals), signals, details)
