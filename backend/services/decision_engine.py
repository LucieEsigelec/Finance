"""Moteur de décision (DecisionEngine) — SPEC §7 à §11.

En bref, ce module répond à cinq questions :

1. **Quelle note finale ?** note = 0,40 × Infos + 0,25 × Graphique + 0,25 × Ratios
   + 0,10 × Hasard (§7.1).
2. **Quel conseil ?** note ≥ 60 → ACHAT ; ≤ 40 → VENTE ; sinon RIEN (§7.2). La note est
   d'abord arrondie au dixième, pour que la note affichée et le conseil concordent.
3. **Pourquoi ?** 2 à 4 phrases en français courant : une par pilier qui pèse dans le
   sens du conseil, plus un point de vigilance. Le hasard n'est jamais cité (§8, RG-03).
4. **Combien sur la semaine ?** 3 scénarios tirés des 52 dernières semaines : central
   = μ + (note − 50) / 50 × σ, favorable = central + σ, défavorable = central − σ (§9).
5. **Que donne l'opération du client ?** nombre d'actions entier, reste en cash,
   verdict, et niveau d'alerte de perte de la semaine (§10, §11, RG-01, RG-05).

Toutes ces fonctions sont « pures » : elles ne lisent ni n'écrivent la base, ce qui
permet de les tester avec les exemples chiffrés de la SPEC (V1 à V16).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Any, Iterable, Mapping

import pandas as pd

import config
from services.common import is_missing, round_half_up
from services.ratio_scoring import RatioResult, estimated_dividend

ACHAT, VENTE, RIEN = "ACHAT", "VENTE", "RIEN"
AUCUN, APPROCHE, ATTEINT = "AUCUN", "APPROCHE", "ATTEINT"
VALIDER = "VALIDER"
NE_RIEN_FAIRE = "NE_RIEN_FAIRE"
PRIVILEGIER_VENTE = "PRIVILEGIER_VENTE"
CONSERVER = "CONSERVER"
REFUSE = "REFUSE"

CENT = Decimal("0.01")

# ---------------------------------------------------------------------------
# 1–2. Note finale et conseil
# ---------------------------------------------------------------------------


def final_score(notes: Mapping[str, float], poids: Mapping[str, float] | None = None) -> float:
    poids = poids or config.POIDS
    return sum(poids[pilier] * notes[pilier] for pilier in poids)


def decide(note: float) -> str:
    note = round_half_up(note, 1)
    if note >= config.SEUIL_ACHAT:
        return ACHAT
    if note <= config.SEUIL_VENTE:
        return VENTE
    return RIEN


def confidence(note: float) -> str:
    gap = abs(round_half_up(note, 1) - config.NOTE_NEUTRE)
    if gap >= config.CONFIANCE_ECART_FORTE:
        return "forte"
    if gap >= config.CONFIANCE_ECART_MOYENNE:
        return "moyenne"
    return "faible"


# ---------------------------------------------------------------------------
# 4. Prévision de la semaine (§9)
# ---------------------------------------------------------------------------


def weekly_returns(history: pd.DataFrame) -> pd.Series:
    """Variations d'une semaine à l'autre (clôture du vendredi), en %."""
    closes = (
        history.assign(date_seance=pd.to_datetime(history["date_seance"]))
        .set_index("date_seance")["close"]
        .astype(float)
        .sort_index()
    )
    weekly = closes.resample("W-FRI").last().dropna()
    return (weekly.pct_change() * 100).dropna()


def forecast(returns: pd.Series, note: float) -> dict[str, float] | None:
    """3 scénarios en %, ou None si moins de 6 mois d'historique."""
    last = returns.iloc[-config.PREVISION_SEMAINES:]
    if len(last) < config.PREVISION_HISTORIQUE_MIN_SEMAINES:
        return None
    mu = float(last.mean())
    sigma = float(last.std(ddof=1))
    central = mu + (note - config.NOTE_NEUTRE) / config.NOTE_ECHELLE * sigma
    return {
        "defavorable": round(central - sigma, 2),
        "central": round(central, 2),
        "favorable": round(central + sigma, 2),
        "mu": round(mu, 3),
        "sigma": round(sigma, 3),
    }


def forecast_euros(scenarios: Mapping[str, float] | None, position_value: Decimal) -> dict[str, int] | None:
    if not scenarios:
        return None
    return {
        k: int((position_value * Decimal(str(scenarios[k])) / 100).quantize(Decimal(1)))
        for k in ("defavorable", "central", "favorable")
    }


# ---------------------------------------------------------------------------
# 5a. Portefeuille et alerte de perte (§10.2, §11)
# ---------------------------------------------------------------------------


def positions(transactions: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """Actions détenues par titre = achetées − vendues (SPEC §10.2)."""
    held: dict[str, int] = {}
    for tx in transactions:
        sign = 1 if tx["type_op"] == ACHAT else -1
        held[tx["ticker"]] = held.get(tx["ticker"], 0) + sign * int(tx["quantite_entiere"])
    return {t: q for t, q in held.items() if q > 0}


def portfolio_value(cash: Decimal, held: Mapping[str, int], prices: Mapping[str, Decimal]) -> Decimal:
    """Valeur = cash + somme (actions détenues × dernier cours)."""
    invested = sum((Decimal(q) * Decimal(str(prices[t])) for t, q in held.items()), Decimal(0))
    return (Decimal(str(cash)) + invested).quantize(CENT)


def weekly_variation_pct(value: Decimal, reference: Decimal) -> float:
    """Performance de la semaine = valeur actuelle / valeur du lundi − 1, en %."""
    if not reference:
        return 0.0
    return float((Decimal(str(value)) / Decimal(str(reference)) - 1) * 100)


def alert_level(variation_pct: float) -> str:
    """RG-01 : APPROCHE à −7 % ou moins, ATTEINT à −10 % ou moins."""
    rounded = round_half_up(variation_pct, 2)
    if rounded <= config.ALERTE_ATTEINT_PCT:
        return ATTEINT
    if rounded <= config.ALERTE_APPROCHE_PCT:
        return APPROCHE
    return AUCUN


def realized_gains(transactions: Iterable[Mapping[str, Any]]) -> dict[str, Decimal]:
    """Gain réalisé sur chaque vente (clé : id de la transaction), méthode du prix moyen :
    gain = actions vendues × (prix de vente − prix d'achat moyen) — SPEC §11.3."""
    quantity: dict[str, int] = {}
    cost: dict[str, Decimal] = {}
    gains: dict[str, Decimal] = {}
    for tx in sorted(transactions, key=lambda t: t["date_execution"]):
        ticker, qty = tx["ticker"], int(tx["quantite_entiere"])
        price = Decimal(str(tx["prix_unitaire"]))
        if tx["type_op"] == ACHAT:
            quantity[ticker] = quantity.get(ticker, 0) + qty
            cost[ticker] = cost.get(ticker, Decimal(0)) + price * qty
        else:
            held = quantity.get(ticker, 0)
            average = cost[ticker] / held if held else Decimal(0)
            gains[tx["id"]] = (qty * (price - average)).quantize(CENT)
            quantity[ticker] = held - qty
            cost[ticker] = cost.get(ticker, Decimal(0)) - average * qty
    return gains


# ---------------------------------------------------------------------------
# 5b. Simulateur (§10)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Operation:
    quantite: int
    montant_reel: Decimal
    reliquat: Decimal
    verdict: str
    motif_refus: str | None
    dividende: Decimal


def fmt_eur(amount: Decimal | float) -> str:
    """49972.8 → « 49 972,80 € » (espace insécable fine pour les milliers)."""
    text = f"{Decimal(str(amount)).quantize(CENT):,.2f}"
    return text.replace(",", " ").replace(".", ",") + " €"


def fmt_pct(value: float, signed: bool = True) -> str:
    text = f"{value:+.1f}" if signed else f"{value:.1f}"
    return text.replace("-", "−").replace(".", ",") + " %"


def verdict(operation: str, conseil: str, niveau_alerte: str) -> str:
    """Croise ce que veut le client et le conseil du titre (§10.3), puis applique
    l'alerte (§11.2) : à l'approche, aucun achat n'est conseillé ; limite atteinte,
    la vente est conseillée."""
    if operation == ACHAT:
        base = {ACHAT: VALIDER, RIEN: NE_RIEN_FAIRE, VENTE: PRIVILEGIER_VENTE}[conseil]
        if niveau_alerte != AUCUN and base == VALIDER:
            return NE_RIEN_FAIRE
        return base
    base = {VENTE: VALIDER, RIEN: NE_RIEN_FAIRE, ACHAT: CONSERVER}[conseil]
    if niveau_alerte == ATTEINT:
        return VALIDER
    return base


def simulate_operation(
    operation: str,
    montant: Decimal,
    cours: Decimal,
    cash: Decimal,
    detenus: int,
    conseil: str,
    niveau_alerte: str,
    dividende_par_action: Decimal | float | None,
) -> Operation:
    montant, cours, cash = Decimal(str(montant)), Decimal(str(cours)), Decimal(str(cash))

    def refused(reason: str) -> Operation:
        return Operation(0, Decimal("0.00"), montant.quantize(CENT), REFUSE, reason, Decimal("0.00"))

    if operation == ACHAT:
        if montant > cash:
            return refused(f"Vous disposez de {fmt_eur(cash)} : le montant dépasse votre cash.")
        quantite = int((montant / cours).to_integral_value(rounding=ROUND_DOWN))
        if quantite == 0:
            return refused(f"Le montant ne permet pas d'acheter une seule action (cours : {fmt_eur(cours)}).")
    else:
        if detenus <= 0:
            return refused("Vous ne détenez pas ce titre : la vente à découvert n'est pas possible.")
        quantite = min(int((montant / cours).to_integral_value(rounding=ROUND_DOWN)), detenus)
        if quantite == 0:
            return refused(f"Le montant est inférieur au cours d'une action ({fmt_eur(cours)}).")

    montant_reel = (cours * quantite).quantize(CENT)
    return Operation(
        quantite=quantite,
        montant_reel=montant_reel,
        reliquat=(montant - montant_reel).quantize(CENT),
        verdict=verdict(operation, conseil, niveau_alerte),
        motif_refus=None,
        dividende=estimated_dividend(quantite, dividende_par_action),
    )


# ---------------------------------------------------------------------------
# 3. Raisons affichées (§8, RG-03)
# ---------------------------------------------------------------------------

TECH_PHRASES = {
    "bollinger": (
        "le cours est proche du bas de sa fourchette habituelle",
        "le cours est au plus haut de sa fourchette habituelle",
    ),
    "rsi": (
        "le titre a beaucoup baissé récemment, un rebond est fréquent",
        "le titre a beaucoup monté récemment, une pause est fréquente",
    ),
    "macd": ("la dynamique repart à la hausse", "la dynamique se retourne à la baisse"),
    "mm": (
        "le cours repasse au-dessus de sa moyenne sur 20 jours",
        "le cours passe sous sa moyenne sur 20 jours",
    ),
    "tendance": ("le cours progresse depuis un mois", "le cours recule depuis un mois"),
}


def _tech_phrases(signals: Mapping[str, float | None], direction: int, limit: int) -> list[str]:
    ranked = sorted(
        (
            (config.IMPORTANCES_TECH[name] * abs(value), name, value)
            for name, value in signals.items()
            if not is_missing(value) and value * direction > 0
        ),
        reverse=True,
    )
    return [TECH_PHRASES[name][0 if value > 0 else 1] for _, name, value in ranked[:limit]]


def _ratio_phrases(ratios: RatioResult | None, direction: int) -> list[str]:
    if ratios is None:
        return []
    phrases = []
    signal = ratios.criteres
    if not is_missing(signal.get("ca")) and signal["ca"] * direction > 0:
        sens = "hausse" if ratios.croissance_ca_pct >= 0 else "baisse"
        phrases.append(f"chiffre d'affaires en {sens} de {fmt_pct(abs(ratios.croissance_ca_pct), False)} sur un an")
    if not is_missing(signal.get("dpa")) and signal["dpa"] * direction > 0:
        sens = "hausse" if ratios.croissance_dpa_pct > 0 else "baisse"
        phrases.append(f"dividende en {sens} de {fmt_pct(abs(ratios.croissance_dpa_pct), False)}")
    if not is_missing(signal.get("rendement")) and signal["rendement"] * direction > 0:
        position = "supérieur" if signal["rendement"] > 0 else "inférieur"
        phrases.append(f"rendement du dividende {position} à la moyenne des 5 titres")
    return phrases


def _info_fact(faits: list[Mapping[str, Any]], direction: int) -> str | None:
    for fait in faits:
        if (fait["score_impact"] - config.NOTE_NEUTRE) * direction > 0:
            return fait["titre"]
    return None


def _pillar_sentence(
    pillar: str,
    direction: int,
    tech_signals: Mapping[str, float | None],
    faits: list[Mapping[str, Any]],
    ratios: RatioResult | None,
) -> str | None:
    if pillar == "infos":
        fact = _info_fact(faits, direction)
        if fact:
            return f"Informations (poids majoritaire) : {fact.rstrip('. ')}."
        tone = "favorables" if direction > 0 else "défavorables"
        return f"Informations (poids majoritaire) : actualités récentes plutôt {tone}."
    if pillar == "tech":
        phrases = _tech_phrases(tech_signals, direction, 2)
        return f"Analyse graphique : {' et '.join(phrases)}." if phrases else None
    phrases = _ratio_phrases(ratios, direction)
    return f"Ratios : {' ; '.join(phrases[:2])}." if phrases else None


def build_reasons(
    note_finale: float,
    conseil: str,
    notes: Mapping[str, float],
    tech_signals: Mapping[str, float | None],
    faits_cles: list[Mapping[str, Any]],
    ratios: RatioResult | None,
    niveau_alerte: str = AUCUN,
    variation_semaine_pct: float = 0.0,
    info_message: str | None = None,
) -> list[str]:
    note = round_half_up(note_finale, 1)
    direction = {ACHAT: 1, VENTE: -1}.get(conseil, 1 if note >= config.NOTE_NEUTRE else -1)
    contributions = {
        p: config.POIDS[p] * (notes[p] - config.NOTE_NEUTRE) for p in ("infos", "tech", "ratios")
    }

    head: list[str] = []
    if niveau_alerte == ATTEINT:
        head.append(
            f"Limite de perte atteinte : {fmt_pct(variation_semaine_pct)} cette semaine. "
            "La vente est conseillée sur les positions en baisse."
        )
    elif niveau_alerte == APPROCHE:
        head.append(
            f"Perte de la semaine proche de la limite ({fmt_pct(variation_semaine_pct)}) : "
            "aucun achat n'est conseillé."
        )
    if conseil == RIEN:
        note_txt = f"{note:.1f}".replace(".", ",")
        if note >= config.NOTE_NEUTRE:
            juste = "juste " if config.SEUIL_ACHAT - note <= 2 else ""
            head.append(
                f"Note de {note_txt}, {juste}sous le seuil d'achat ({config.SEUIL_ACHAT:.0f}) : "
                "signaux plutôt favorables mais pas assez nets."
            )
        else:
            juste = "juste " if note - config.SEUIL_VENTE <= 2 else ""
            head.append(
                f"Note de {note_txt}, {juste}au-dessus du seuil de vente ({config.SEUIL_VENTE:.0f}) : "
                "signaux plutôt défavorables mais pas assez nets."
            )

    supporting = []
    for pillar, points in sorted(contributions.items(), key=lambda kv: kv[1] * direction, reverse=True):
        if points * direction < config.RAISON_PILIER_MIN_POINTS:
            break
        sentence = _pillar_sentence(pillar, direction, tech_signals, faits_cles, ratios)
        if sentence:
            supporting.append(sentence)

    vigilance = None
    opposing = min(contributions.items(), key=lambda kv: kv[1] * direction)
    if opposing[1] * direction <= -config.RAISON_PILIER_MIN_POINTS:
        sentence = _pillar_sentence(opposing[0], -direction, tech_signals, faits_cles, ratios)
        if sentence:
            vigilance = "Point de vigilance — " + sentence[0].lower() + sentence[1:]
    if vigilance is None:
        contrary = _tech_phrases(
            {k: v for k, v in tech_signals.items() if not is_missing(v) and abs(v) >= 0.5}, -direction, 1
        )
        if contrary:
            vigilance = f"Point de vigilance : {contrary[0]}."

    room = config.RAISONS_MAX - len(head) - (1 if vigilance else 0)
    reasons = head + supporting[: max(room, 0)]
    if vigilance and len(reasons) < config.RAISONS_MAX:
        reasons.append(vigilance)
    if len(reasons) < config.RAISONS_MIN and info_message:
        reasons.append(f"Informations : {info_message}.")
    if len(reasons) < config.RAISONS_MIN:
        reasons.append("Aucun pilier ne se détache nettement : les signaux se compensent.")
    return reasons[: config.RAISONS_MAX]
