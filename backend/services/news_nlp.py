"""Analyse des actualités par un modèle de langue : Claude Haiku 5.5 (D-16).

En bref : pour chaque action, les NOUVEAUX articles (titre + résumé) sont envoyés en un
seul appel à Claude, qui répond pour chacun :
- le **sentiment** pour l'actionnaire, entre −1 (très négatif) et +1 (très positif) ; il
  comprend le contexte (« baisse des coûts » est une bonne nouvelle, « bat le consensus »
  aussi), en français comme en anglais ;
- si c'est une **annonce officielle** de l'entreprise (résultats, contrat, acquisition,
  dividende, dirigeant, avertissement…) : elle pèse deux fois plus (SPEC §4.1) ;
- si l'article **concerne vraiment l'entreprise** (sinon il est écarté).

La note d'impact reste celle de la SPEC : 50 + 50 × sentiment × importance.

Chaque article n'est analysé qu'une fois, à la collecte ; la note est rangée en base.
Sans clé ``ANTHROPIC_API_KEY``, ou si l'appel échoue (réseau, refus, réponse invalide),
on revient à l'analyse par lexique (``services/sentiment.py``) : l'actualisation ne
s'arrête jamais à cause du modèle.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Sequence

import config
from services.common import clip

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es analyste financier. On te donne des titres et résumés d'articles de presse \
(français ou anglais) trouvés en cherchant une entreprise cotée à Paris. Pour chaque article, évalue \
l'effet probable de la nouvelle sur le cours de l'action de CETTE entreprise, du point de vue d'un \
actionnaire, sur la semaine à venir.

- sentiment : nombre entre -1 (très défavorable) et 1 (très favorable) ; 0 si neutre ou purement \
factuel (simple variation de cours sans cause, agenda, palmarès). Raisonne sur le sens économique, \
pas sur les mots : « baisse des coûts », « relève sa prévision », « bat le consensus » sont favorables ; \
« objectif abaissé », « enquête », « avertissement sur résultats » sont défavorables.
- annonce_officielle : true si l'article rapporte une communication de l'entreprise elle-même \
(résultats, prévisions, contrat important, acquisition ou cession, dividende, changement de \
dirigeant, avertissement) ; false pour un commentaire, une analyse de broker ou une rumeur.
- concerne_entreprise : false si l'article ne parle pas vraiment de cette entreprise (homonyme, \
simple citation dans une liste, autre société).

Réponds pour TOUS les articles, avec le même index que dans la liste."""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "articles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "sentiment": {"type": "number"},
                    "annonce_officielle": {"type": "boolean"},
                    "concerne_entreprise": {"type": "boolean"},
                },
                "required": ["index", "sentiment", "annonce_officielle", "concerne_entreprise"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["articles"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Analysis:
    sentiment: float
    annonce: bool
    pertinent: bool


class NlpUnavailable(Exception):
    """Le modèle n'a pas pu analyser le lot : on garde l'analyse par lexique."""


def build_prompt(company: str, ticker: str, articles: Sequence[dict[str, Any]]) -> str:
    lines = [f"Entreprise : {company} ({ticker}, Euronext Paris)", "", "Articles :"]
    for index, article in enumerate(articles):
        resume = (article.get("resume") or "").strip()
        lines.append(f"[{index}] {article['titre'].strip()}" + (f" — {resume[:400]}" if resume else ""))
    return "\n".join(lines)


def parse_response(text: str, count: int) -> list[Analysis]:
    """Lit la réponse JSON ; chaque article doit avoir sa ligne (sinon NlpUnavailable)."""
    try:
        rows = json.loads(text)["articles"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise NlpUnavailable(f"réponse illisible : {error}") from error
    by_index = {}
    for row in rows:
        try:
            by_index[int(row["index"])] = Analysis(
                sentiment=clip(float(row["sentiment"])),
                annonce=bool(row["annonce_officielle"]),
                pertinent=bool(row["concerne_entreprise"]),
            )
        except (KeyError, TypeError, ValueError):
            continue
    if set(by_index) != set(range(count)):
        raise NlpUnavailable(f"{count - len(set(by_index) & set(range(count)))} article(s) sans réponse")
    return [by_index[i] for i in range(count)]


class ClaudeNewsAnalyzer:
    """Note les articles avec Claude Haiku 5.5, par lots (un appel pour au plus 40 articles)."""

    def __init__(self, client: Any, model: str = config.NLP_MODELE):
        self.client = client
        self.model = model

    @classmethod
    def from_settings(cls) -> "ClaudeNewsAnalyzer | None":
        """None si aucune clé n'est configurée : l'application utilise alors le lexique."""
        key = config.load_settings().anthropic_api_key
        if not key:
            return None
        import anthropic

        return cls(anthropic.Anthropic(api_key=key, max_retries=3, timeout=config.NLP_TIMEOUT_SECONDES))

    def analyze(self, company: str, ticker: str, articles: Sequence[dict[str, Any]]) -> list[Analysis]:
        results: list[Analysis] = []
        size = config.NLP_ARTICLES_PAR_APPEL
        for start in range(0, len(articles), size):
            results += self._analyze_batch(company, ticker, articles[start:start + size])
        return results

    def _analyze_batch(self, company: str, ticker: str, batch: Sequence[dict[str, Any]]) -> list[Analysis]:
        import anthropic

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": RESPONSE_SCHEMA}},
                messages=[{"role": "user", "content": build_prompt(company, ticker, batch)}],
            )
        except anthropic.APIConnectionError as error:
            raise NlpUnavailable("connexion au modèle impossible") from error
        except anthropic.RateLimitError as error:
            raise NlpUnavailable("limite d'appels du modèle atteinte") from error
        except anthropic.APIStatusError as error:
            raise NlpUnavailable(f"erreur du modèle ({error.status_code})") from error
        if response.stop_reason in ("refusal", "max_tokens"):
            raise NlpUnavailable(f"réponse incomplète ({response.stop_reason})")
        text = next((block.text for block in response.content if block.type == "text"), "")
        return parse_response(text, len(batch))


def apply_analysis(articles: list[dict[str, Any]], analyses: Sequence[Analysis]) -> list[dict[str, Any]]:
    """Remplace la note d'impact par celle du modèle et retire les articles hors sujet."""
    from services.info_scoring import impact_score

    kept = []
    for article, analysis in zip(articles, analyses):
        if not analysis.pertinent:
            continue
        kept.append({**article, "score_impact": round(impact_score(analysis.sentiment, analysis.annonce), 2)})
    return kept
