"""Note de sentiment d'un article (positif / négatif), en français et en anglais — SPEC §4.1.

En bref : on cherche dans le titre et le résumé des mots positifs (« hausse »,
« contrat », « record »…) et négatifs (« baisse », « avertissement », « chute »…).
Le sentiment s vaut (positifs − négatifs) / (positifs + négatifs + 1), donc entre
−1 et +1. Un mot précédé d'une négation (« pas », « not ») compte à l'envers.

On repère aussi les **annonces officielles** (résultats, contrat, fusion, changement
de dirigeant, avertissement) : elles pèsent deux fois plus (importance 1 au lieu de 0,5).

C'est une méthode simple par mots-clés, choisie pour le prototype : gratuite, rapide,
explicable, et légère pour l'hébergement. Elle pourra être remplacée par un modèle
d'analyse de texte plus fin sans toucher au reste du code (voir docs/decisions.md D-06).
"""

from __future__ import annotations

import re
import unicodedata

POSITIVE = {
    # français
    "hausse", "hausses", "progresse", "progression", "croissance", "record", "records", "bondit",
    "bond", "grimpe", "rebond", "rebondit", "contrat", "contrats", "accord", "accords", "succes",
    "solide", "solides", "depasse", "superieur", "superieurs", "relevement", "releve", "releve",
    "optimiste", "optimisme", "benefice", "benefices", "gagne", "gain", "gains", "acquisition",
    "renforce", "achat", "surperforme", "favorable", "favorables", "dynamique", "embellie",
    "couleurs", "relance", "partenariat", "innovation", "lance", "confirme", "ameliore", "amelioration",
    # anglais
    "rise", "rises", "rising", "gain", "gains", "growth", "grows", "record", "jump", "jumps", "surge",
    "surges", "beat", "beats", "strong", "upgrade", "upgrades", "upgraded", "raise", "raises", "raised",
    "profit", "profits", "contract", "contracts", "deal", "wins", "win", "rally", "outperform",
    "bullish", "positive", "boost", "boosts", "expands", "partnership", "buy",
}

NEGATIVE = {
    # français
    "baisse", "baisses", "recule", "recul", "chute", "chutes", "plonge", "decroche", "perte", "pertes",
    "avertissement", "deception", "decevant", "decevante", "decevants", "inferieur", "inferieurs",
    "abaisse", "abaissement", "degrade", "degradation", "prudent", "prudente", "prudence", "inquietude",
    "inquietudes", "risque", "risques", "menace", "menaces", "enquete", "amende", "greve", "licenciement",
    "licenciements", "suppression", "suppressions", "ralentissement", "ralentit", "difficile",
    "difficultes", "crise", "vente", "sanction", "sanctions", "litige", "proces", "defavorable",
    # anglais
    "fall", "falls", "falling", "drop", "drops", "decline", "declines", "loss", "losses", "warning",
    "warns", "miss", "misses", "weak", "downgrade", "downgrades", "downgraded", "cut", "cuts", "lawsuit",
    "probe", "fine", "fined", "strike", "layoffs", "slowdown", "slump", "plunge", "plunges", "bearish",
    "negative", "risk", "risks", "concern", "concerns", "sell",
}

NEGATIONS = {"pas", "ne", "non", "sans", "not", "no", "without"}

# Annonce officielle : résultats, gros contrat, avertissement, fusion, changement de dirigeant
ANNOUNCEMENT = re.compile(
    r"\b(resultats?|chiffre d.affaires|trimestriel|semestriel|annuel|guidance|objectifs?|"
    r"contrats?|acquisition|rachat|fusion|cession|avertissement|directeur general|pdg|ceo|"
    r"nomination|nomme|demission|dividende|results?|earnings|revenue|quarterly|outlook|"
    r"contract|acquires?|acquisition|merger|takeover|profit warning|appoints?|steps down)\b"
)


def _normalize(text: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(ch for ch in plain if not unicodedata.combining(ch))
    return re.findall(r"[a-z]+", plain)


def sentiment(text: str) -> float:
    """Sentiment entre −1 (très négatif) et +1 (très positif)."""
    words = _normalize(text)
    positive = negative = 0
    for i, word in enumerate(words):
        polarity = (word in POSITIVE) - (word in NEGATIVE)
        if polarity == 0:
            continue
        if any(w in NEGATIONS for w in words[max(0, i - 2):i]):
            polarity = -polarity
        if polarity > 0:
            positive += 1
        else:
            negative += 1
    return (positive - negative) / (positive + negative + 1)


def is_announcement(text: str) -> bool:
    return bool(ANNOUNCEMENT.search(" ".join(_normalize(text))))
