"""Réglages de l'application : tous les nombres du moteur sont ici, nulle part ailleurs.

En bref :
- la première partie lit les secrets et adresses dans le fichier ``backend/.env`` ;
- la seconde regroupe les poids, seuils et durées fixés par la spécification (SPEC) ;
- ``check_rg04`` vérifie, dès le chargement, que le pilier Informations pèse
  strictement plus que chacun des trois autres (règle RG-04). Sinon l'application
  refuse de démarrer (cas de vérification V8).

Pour changer un réglage, on modifie ce fichier et on relance les tests : le code des
services n'a jamais besoin d'être touché (SPEC §1.3).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Final, Mapping

from dotenv import load_dotenv

BACKEND_DIR: Final = Path(__file__).resolve().parent

# Lit backend/.env s'il existe. Une variable déjà définie dans le système (Render,
# GitHub Actions) garde la priorité.
load_dotenv(BACKEND_DIR / ".env", encoding="utf-8")


class ConfigError(RuntimeError):
    """Réglage invalide : l'application ne doit pas démarrer."""


# ---------------------------------------------------------------------------
# 1. Environnement (secrets et adresses) — CLAUDE.md §6.2
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_key: str
    news_api_key: str
    cors_origins: tuple[str, ...]

    def __repr__(self) -> str:  # ne jamais afficher une clé, même par erreur
        return (
            f"Settings(supabase_url={self.supabase_url!r}, supabase_key=***, "
            f"news_api_key=***, cors_origins={self.cors_origins!r})"
        )


def load_settings() -> Settings:
    origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return Settings(
        supabase_url=os.getenv("SUPABASE_URL", "").strip(),
        supabase_key=os.getenv("SUPABASE_KEY", "").strip(),
        news_api_key=os.getenv("NEWS_API_KEY", "").strip(),
        cors_origins=tuple(o.strip().rstrip("/") for o in origins.split(",") if o.strip()),
    )


# ---------------------------------------------------------------------------
# 2. Univers et portefeuille — CdCF §2, DCT §4
# ---------------------------------------------------------------------------

TICKERS: Final = ("DSY.PA", "TTE.PA", "CAP.PA", "RMS.PA", "AI.PA")
CAPITAL_INITIAL: Final = Decimal("500000.00")

# ---------------------------------------------------------------------------
# 2 bis. Collecte des données — DCT §2.1, UI §6.3
# ---------------------------------------------------------------------------

# Recherche d'actualités par titre (Google News RSS en français + NewsAPI)
NEWS_QUERIES: Final[Mapping[str, str]] = {
    "DSY.PA": '"Dassault Systèmes"',
    "TTE.PA": '"TotalEnergies"',
    "CAP.PA": '"Capgemini"',
    "RMS.PA": '"Hermès International" OR "Hermès" luxe',
    "AI.PA": '"Air Liquide"',
}
# Un article n'est gardé que s'il cite l'entreprise (texte en minuscules, sans accents)…
NEWS_MOTS_CLES: Final[Mapping[str, tuple[str, ...]]] = {
    "DSY.PA": ("dassault systemes", "3ds", "solidworks", "catia"),
    "TTE.PA": ("totalenergies", "total energies"),
    "CAP.PA": ("capgemini",),
    "RMS.PA": ("hermes",),
    "AI.PA": ("air liquide",),
}
# … et s'il n'est pas une simple page de cotation.
NEWS_BRUIT: Final = ("cours action", "cotation bourse", "cours de bourse en temps reel")
NEWS_MAX_ARTICLES_PAR_SOURCE: Final = 15
HTTP_TIMEOUT_SECONDES: Final = 20
# Le bouton « Actualiser » est public : au plus une actualisation toutes les 2 minutes (D-11)…
REFRESH_INTERVALLE_MIN_SECONDES: Final = 120
# … et NewsAPI (gratuit : 100 requêtes / jour, 5 par actualisation) au plus toutes les 15 minutes.
NEWSAPI_INTERVALLE_MIN_SECONDES: Final = 900
# Données de plus d'une heure : le tableau de bord relance l'actualisation tout seul (D-13).
DONNEES_AGE_MAX_SECONDES: Final = 3600

# ---------------------------------------------------------------------------
# 3. Échelle des notes — SPEC §1.2 : note = 50 + 50 × signal
# ---------------------------------------------------------------------------

NOTE_NEUTRE: Final = 50.0
NOTE_ECHELLE: Final = 50.0

# ---------------------------------------------------------------------------
# 4. Pilier Analyse graphique — SPEC §3
# ---------------------------------------------------------------------------

MM_PERIODES: Final = (20, 50, 200)
# Écart (en %) qui donne un signal de +1 : cours/MM20, MM20/MM50, MM50/MM200
MM_ECARTS_PCT: Final = (2.0, 3.0, 5.0)
# La comparaison cours/MM20 compte double (horizon d'une semaine)
MM_COEFFICIENTS: Final = (2, 1, 1)

TENDANCE_JOURS: Final = 20
TENDANCE_PCT_HEBDO_MAX: Final = 3.0  # +3 %/semaine → signal +1

MACD_RAPIDE: Final = 12
MACD_LENTE: Final = 26
MACD_SIGNAL: Final = 9
MACD_SIGNAL_CROISEMENT: Final = 1.0  # vient de croiser
MACD_SIGNAL_MAINTIEN: Final = 0.5  # reste du même côté
# « Vient de passer » = croisement pendant les 5 dernières séances (une semaine).
# Précision ajoutée (SPEC §3.3 ne chiffre pas la durée) — voir docs/decisions.md D-06.
MACD_FENETRE_CROISEMENT_SEANCES: Final = 5

BOLLINGER_PERIODE: Final = 20
BOLLINGER_ECARTS_TYPES: Final = 2

RSI_PERIODE: Final = 14
RSI_CENTRE: Final = 50.0
RSI_ECHELLE: Final = 20.0  # RSI 30 → +1, RSI 70 → −1

IMPORTANCES_TECH: Final[Mapping[str, int]] = {
    "bollinger": 9,
    "rsi": 7,
    "macd": 6,
    "mm": 5,
    "tendance": 5,
}

# ---------------------------------------------------------------------------
# 5. Pilier Informations — SPEC §4
# ---------------------------------------------------------------------------

INFO_DEMI_VIE_JOURS: Final = 2.0
INFO_FENETRE_JOURS: Final = 7
INFO_IMPORTANCE_ANNONCE: Final = 1.0
INFO_IMPORTANCE_ORDINAIRE: Final = 0.5
INFO_NB_FAITS_CLES: Final = 3

# ---------------------------------------------------------------------------
# 6. Pilier Ratios financiers — SPEC §5
# ---------------------------------------------------------------------------

RATIO_CA_CROISSANCE_NEUTRE_PCT: Final = 5.0  # +5 % → signal 0
RATIO_CA_CROISSANCE_MAX_PCT: Final = 10.0  # +10 % → signal +1
RATIO_DPA_HAUSSE_PCT: Final = 1.0  # hausse de plus de 1 % → +1 ; baisse de plus de 1 % → −1 ; sinon stable (0)
RATIO_RENDEMENT_ECART_MAX: Final = 0.5  # ±50 % de la moyenne des 5 → ±1

IMPORTANCES_RATIOS: Final[Mapping[str, int]] = {
    "ca": 7,
    "dpa": 6,
    "rendement": 6,
}

# ---------------------------------------------------------------------------
# 7. Décision — SPEC §7
# ---------------------------------------------------------------------------

# Importances données par le client : 8 / 5 / 5 / 2 sur 20
POIDS: Final[Mapping[str, float]] = {
    "infos": 0.40,
    "tech": 0.25,
    "ratios": 0.25,
    "hasard": 0.10,
}

def _threshold(name: str, default: float) -> float:
    """Seuil lu dans l'environnement (essai sans toucher au code), sinon valeur de la SPEC."""
    raw = os.getenv(name, "").strip().replace(",", ".")
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as error:
        raise ConfigError(f"{name} doit être un nombre, reçu {raw!r}") from error


# SPEC §7.2 : 60 / 40. Réglables par SEUIL_ACHAT / SEUIL_VENTE pour un essai (D-10) ;
# le contrôle check_config impose toujours SEUIL_VENTE < 50 < SEUIL_ACHAT.
SEUIL_ACHAT: Final = _threshold("SEUIL_ACHAT", 60.0)  # note ≥ SEUIL_ACHAT → ACHAT
SEUIL_VENTE: Final = _threshold("SEUIL_VENTE", 40.0)  # note ≤ SEUIL_VENTE → VENTE

RAISONS_MIN: Final = 2
RAISONS_MAX: Final = 4
# Un pilier « pèse » s'il déplace la note finale d'au moins 1 point (poids × écart à 50).
RAISON_PILIER_MIN_POINTS: Final = 1.0

# Confiance affichée (SPEC §7.2 ne chiffre pas les paliers) : écart de la note à 50.
# Proposition provisoire — voir docs/decisions.md D-06.
CONFIANCE_ECART_MOYENNE: Final = 15.0  # < 15 points → faible
CONFIANCE_ECART_FORTE: Final = 25.0  # ≥ 25 points → forte

# ---------------------------------------------------------------------------
# 8. Prévision de la semaine — SPEC §9
# ---------------------------------------------------------------------------

PREVISION_SEMAINES: Final = 52
PREVISION_HISTORIQUE_MIN_SEMAINES: Final = 26  # moins de 6 mois → pas de prévision
HISTORIQUE_INITIAL_ANNEES: Final = 2  # chargé au premier refresh (MM200, 52 semaines)

# Graphiques 1 jour / 1 semaine (D-12) : bougies de 5 min sur 5 séances, regroupées par
# 30 min pour la vue « semaine » ; on garde 10 jours en base.
INTRADAY_PERIODE: Final = "5d"
INTRADAY_INTERVALLE: Final = "5m"
INTRADAY_REGROUPEMENT_SEMAINE: Final = "30min"
INTRADAY_CONSERVATION_JOURS: Final = 10

# ---------------------------------------------------------------------------
# 9. Simulateur et transactions — SPEC §10, A.4
# ---------------------------------------------------------------------------

FRAIS_PCT: Final = Decimal("0")
CONSEIL_VALIDITE_MINUTES: Final = 5

# ---------------------------------------------------------------------------
# 10. Garde-fou et historique — SPEC §11, RG-01, RG-06
# ---------------------------------------------------------------------------

ALERTE_APPROCHE_PCT: Final = -7.0
ALERTE_ATTEINT_PCT: Final = -10.0
HISTORIQUE_HORIZON_JOURS: Final = 365


# ---------------------------------------------------------------------------
# Contrôles au démarrage
# ---------------------------------------------------------------------------

_PILIERS: Final = ("infos", "tech", "ratios", "hasard")


def check_rg04(poids: Mapping[str, float]) -> None:
    """RG-04 : le poids des Informations est strictement supérieur aux trois autres.

    Vérifie aussi que les quatre poids existent, sont positifs et font 100 %.
    Lève ``ConfigError`` sinon (V8 : l'application refuse de démarrer).
    """
    if set(poids) != set(_PILIERS):
        raise ConfigError(f"POIDS doit contenir exactement {_PILIERS}, reçu {tuple(poids)}")
    if any(p < 0 for p in poids.values()):
        raise ConfigError("POIDS : aucun poids ne peut être négatif")
    if abs(sum(poids.values()) - 1.0) > 1e-9:
        raise ConfigError(f"POIDS : la somme doit valoir 1, elle vaut {sum(poids.values())}")
    autres = [p for nom, p in poids.items() if nom != "infos"]
    if not all(poids["infos"] > p for p in autres):
        raise ConfigError(
            "RG-04 : le poids des Informations doit être strictement supérieur "
            f"à celui des autres piliers (reçu {dict(poids)})"
        )


def check_config() -> None:
    """Tous les contrôles de cohérence des réglages."""
    check_rg04(POIDS)
    if not SEUIL_VENTE < NOTE_NEUTRE < SEUIL_ACHAT:
        raise ConfigError("Seuils : il faut SEUIL_VENTE < 50 < SEUIL_ACHAT")
    if not ALERTE_ATTEINT_PCT < ALERTE_APPROCHE_PCT < 0:
        raise ConfigError("Alerte : il faut ALERTE_ATTEINT_PCT < ALERTE_APPROCHE_PCT < 0")
    if not 0 < CONFIANCE_ECART_MOYENNE < CONFIANCE_ECART_FORTE <= NOTE_ECHELLE:
        raise ConfigError("Confiance : il faut 0 < ECART_MOYENNE < ECART_FORTE <= 50")
    if not 0 < RAISONS_MIN <= RAISONS_MAX:
        raise ConfigError("Raisons : il faut 0 < RAISONS_MIN <= RAISONS_MAX")
    if set(IMPORTANCES_TECH) != {"bollinger", "rsi", "macd", "mm", "tendance"}:
        raise ConfigError("IMPORTANCES_TECH : les 5 indicateurs de la SPEC §3.2 sont attendus")
    if set(IMPORTANCES_RATIOS) != {"ca", "dpa", "rendement"}:
        raise ConfigError("IMPORTANCES_RATIOS : les 3 critères de la SPEC §5 sont attendus")


# Contrôle dès le chargement du module : un réglage invalide empêche tout démarrage.
check_config()
