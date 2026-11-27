"""Lecture détaillée du graphique : moyennes mobiles, croisements, supports et résistances.

En bref : transforme les cours en quelques phrases claires pour le client (« le cours est
au-dessus de ses trois moyennes », « support vers 74,20 € »). C'est une EXPLICATION : rien
ici n'entre dans la note ni dans le conseil, qui restent ceux de la SPEC §3 (D-24).

Supports / résistances (hors SPEC, méthode simple et expliquable) :
1. on repère sur 6 mois les sommets et les creux (plus haut / plus bas sur ±5 séances) ;
2. on regroupe ceux qui sont à moins de 1,5 % les uns des autres : c'est un « niveau » ;
3. un niveau touché au moins 2 fois compte ; sous le cours c'est un support, au-dessus une résistance.
Aucune donnée postérieure à ``date_calcul`` n'est utilisée.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

import config
from services.common import is_missing
from services.decision_engine import fmt_eur, fmt_pct
from services.technical_scoring import compute_indicators

NOMS_MM = {"mm20": "20 jours", "mm50": "50 jours", "mm200": "200 jours"}


def _pct(value: float, reference: float) -> float:
    return round((value / reference - 1) * 100, 1)


def find_pivots(df: pd.DataFrame, half: int) -> list[tuple[float, str]]:
    """Sommets (haut le plus haut sur ±half séances) et creux (bas le plus bas)."""
    highs = df["high"].fillna(df["close"]).to_numpy(dtype=float)
    lows = df["low"].fillna(df["close"]).to_numpy(dtype=float)
    pivots = []
    for i in range(half, len(df) - half):
        window = slice(i - half, i + half + 1)
        if highs[i] == highs[window].max():
            pivots.append((float(highs[i]), "sommet"))
        if lows[i] == lows[window].min():
            pivots.append((float(lows[i]), "creux"))
    return pivots


def cluster_levels(prices: list[float], tolerance_pct: float) -> list[dict[str, Any]]:
    """Regroupe des prix proches (à moins de tolerance_pct de la moyenne du groupe)."""
    levels: list[list[float]] = []
    for price in sorted(prices):
        if levels and abs(price / (sum(levels[-1]) / len(levels[-1])) - 1) * 100 <= tolerance_pct:
            levels[-1].append(price)
        else:
            levels.append([price])
    return [{"niveau": round(sum(g) / len(g), 2), "touches": len(g)} for g in levels]


def support_resistance(df: pd.DataFrame, close: float) -> tuple[list[dict], list[dict]]:
    window = df.tail(config.SR_FENETRE_SEANCES)
    pivots = find_pivots(window, config.SR_PIVOT_DEMI_FENETRE)
    levels = [lv for lv in cluster_levels([p for p, _ in pivots], config.SR_REGROUPEMENT_PCT)
              if lv["touches"] >= config.SR_TOUCHES_MIN]
    supports = sorted((lv for lv in levels if lv["niveau"] < close), key=lambda lv: -lv["niveau"])
    resistances = sorted((lv for lv in levels if lv["niveau"] > close), key=lambda lv: lv["niveau"])
    # Repli : à défaut de niveau touché 2 fois, le plus bas / plus haut de 6 mois.
    if not supports and not window.empty:
        low = float(window["low"].fillna(window["close"]).min())
        if low < close:
            supports = [{"niveau": round(low, 2), "touches": 1, "extreme": True}]
    if not resistances and not window.empty:
        high = float(window["high"].fillna(window["close"]).max())
        if high > close:
            resistances = [{"niveau": round(high, 2), "touches": 1, "extreme": True}]
    for lv in supports + resistances:
        lv["ecart_pct"] = _pct(lv["niveau"], close)
    return supports[: config.SR_NOMBRE], resistances[: config.SR_NOMBRE]


def recent_cross(df: pd.DataFrame, fast: str, slow: str, sessions: int) -> dict[str, Any] | None:
    """Dernier croisement de deux moyennes pendant les ``sessions`` dernières séances."""
    pair = df[[fast, slow]].dropna().tail(sessions + 1)
    if len(pair) < 2:
        return None
    above = (pair[fast] > pair[slow]).to_numpy()
    for back in range(1, len(above)):
        i = len(above) - back
        if above[i] != above[i - 1]:
            return {"sens": "hausse" if above[i] else "baisse", "il_y_a": back - 1,
                    "rapide": fast, "lente": slow}
    return None


def _ma_sentences(close: float, mms: dict[str, float]) -> list[str]:
    above = [k for k, v in mms.items() if close > v]
    below = [k for k in mms if k not in above]
    cours = fmt_eur(close)
    if len(mms) == 3 and len(above) == 3:
        first = (f"Le cours ({cours}) est au-dessus de ses trois moyennes (20, 50 et 200 jours) : "
                 "la tendance est haussière à court, moyen et long terme.")
    elif len(mms) == 3 and not above:
        first = (f"Le cours ({cours}) est sous ses trois moyennes (20, 50 et 200 jours) : "
                 "la tendance est baissière à court, moyen et long terme.")
    else:
        def days(keys):  # ["mm20", "mm50"] → « 20 et 50 jours »
            return " et ".join(k[2:] for k in keys) + " jours"

        parts = []
        if above:
            parts.append(("au-dessus de sa moyenne sur " if len(above) == 1 else "au-dessus de ses moyennes sur ") + days(above))
        if below:
            parts.append(("sous celle sur " if len(below) == 1 else "sous celles sur ") + days(below))
        fond = ""
        if "mm200" in mms:
            fond = (" : la tendance de fond reste haussière, le court terme hésite" if "mm200" in above
                    else " : la tendance de fond reste baissière, malgré un court terme plus ferme")
        first = f"Le cours ({cours}) est " + ", mais ".join(parts) + fond + "."
    sentences = [first]
    if len(mms) == 3:
        if mms["mm20"] > mms["mm50"] > mms["mm200"]:
            suite = ("signe d'une hausse installée" if close >= mms["mm20"]
                     else "la hausse de fond tient, le repli récent ressemble pour l'instant à une pause")
            sentences.append(f"Les moyennes sont rangées à la hausse (20 j au-dessus de 50 j, elle-même au-dessus de 200 j) : {suite}.")
        elif mms["mm20"] < mms["mm50"] < mms["mm200"]:
            suite = ("signe d'une baisse installée" if close <= mms["mm20"]
                     else "la baisse de fond domine, le rebond récent reste à confirmer")
            sentences.append(f"Les moyennes sont rangées à la baisse (20 j sous 50 j, elle-même sous 200 j) : {suite}.")
        else:
            sentences.append("Les moyennes s'entrecroisent : la tendance n'est pas nette.")
    return sentences


def _cross_sentence(cross: dict[str, Any]) -> str:
    quand = "aujourd'hui" if cross["il_y_a"] == 0 else f"il y a {cross['il_y_a']} séance{'s' if cross['il_y_a'] > 1 else ''}"
    rapide, lente = NOMS_MM[cross["rapide"]], NOMS_MM[cross["lente"]]
    position = "au-dessus" if cross["sens"] == "hausse" else "en dessous"
    if cross["lente"] == "mm200":
        nom = "« croisement doré », signal haussier de fond" if cross["sens"] == "hausse" else \
              "« croisement de la mort », signal baissier de fond"
        return f"{quand.capitalize()}, la moyenne {rapide} est passée {position} de la {lente} ({nom} très suivi)."
    sens = "haussier" if cross["sens"] == "hausse" else "baissier"
    return f"{quand.capitalize()}, la moyenne {rapide} est passée {position} de la {lente} : signal {sens} de court terme."


def _level_sentence(level: dict[str, Any], kind: str) -> str:
    prix, ecart = fmt_eur(level["niveau"]), fmt_pct(level["ecart_pct"])
    if level.get("extreme"):
        return (f"Support : le plus bas de 6 mois, {prix} ({ecart})." if kind == "support"
                else f"Résistance : le plus haut de 6 mois, {prix} ({ecart}).")
    if kind == "support":
        return (f"Support vers {prix} ({ecart}) : le cours s'est arrêté {level['touches']} fois sur ce niveau "
                "ces 6 derniers mois. S'il passait dessous, la baisse pourrait s'accélérer.")
    return (f"Résistance vers {prix} ({ecart}) : le cours s'est arrêté {level['touches']} fois sur ce niveau "
            "ces 6 derniers mois. Le franchir serait un signal de hausse.")


def analyze_chart(history: pd.DataFrame, date_calcul: date) -> dict[str, Any] | None:
    """Analyse graphique détaillée au ``date_calcul`` ; None sans cours."""
    if history is None or history.empty:
        return None
    past = history[pd.to_datetime(history["date_seance"]).dt.date <= date_calcul]
    if past.empty:
        return None
    df = compute_indicators(past)
    last = df.iloc[-1]
    close = float(last["close"])
    mms = {k: float(last[k]) for k in NOMS_MM if not is_missing(last[k])}

    moyennes = [{"nom": k, "libelle": f"Moyenne {NOMS_MM[k]}", "valeur": round(v, 2), "ecart_pct": _pct(close, v)}
                for k, v in mms.items()]
    croisements = [c for c in (recent_cross(df, "mm50", "mm200", config.CROISEMENT_RECENT_SEANCES),
                               recent_cross(df, "mm20", "mm50", config.CROISEMENT_RECENT_SEANCES)) if c]
    supports, resistances = support_resistance(df, close)

    lecture = _ma_sentences(close, mms) if mms else ["Pas encore assez d'historique pour les moyennes mobiles."]
    lecture += [_cross_sentence(c) for c in croisements]
    if supports:
        lecture.append(_level_sentence(supports[0], "support"))
    if resistances:
        lecture.append(_level_sentence(resistances[0], "resistance"))
    else:
        lecture.append("Le cours est à son plus haut de 6 mois : aucune résistance récente au-dessus.")
    if not supports:
        lecture.append("Le cours est à son plus bas de 6 mois : aucun support récent en dessous.")
    # Moyenne juste sous / sur le cours : support ou résistance « mobile ».
    for k, v in sorted(mms.items(), key=lambda kv: abs(close - kv[1])):
        ecart = _pct(v, close)
        if abs(ecart) <= config.MM_SUPPORT_PROCHE_PCT and k != "mm20":
            role = "support" if v < close else "résistance"
            lecture.append(f"La moyenne {NOMS_MM[k]} ({fmt_eur(v)}, {fmt_pct(ecart)}) est tout proche : "
                           f"elle sert souvent de {role}.")
            break
    near = [(lv, "support") for lv in supports[:1]] + [(lv, "résistance") for lv in resistances[:1]]
    for lv, role in near:
        if abs(lv["ecart_pct"]) <= config.SR_PROCHE_PCT:
            suite = "un rebond ou une cassure se joue maintenant" if role == "support" else \
                    "un rejet ou une cassure se joue maintenant"
            lecture.append(f"Le cours est tout près de sa {role} : {suite}.")

    return {
        "cours": round(close, 2),
        "date": last["date_seance"].isoformat(),
        "moyennes": moyennes,
        "croisements": croisements,
        "supports": supports,
        "resistances": resistances,
        "lecture": lecture,
    }
