"""Renote avec Claude les actualités des 7 derniers jours déjà en base (D-16).

En bref : à lancer une fois après avoir ajouté ANTHROPIC_API_KEY, pour que les articles
notés par l'ancien lexique (souvent 50) soient remplacés par la note du modèle. Les
articles que le modèle juge hors sujet passent à 50 (neutre) — rien n'est supprimé.
ÉCRIT dans la base (colonne actualites.score_impact). Les conseils sont recalculés à la
prochaine actualisation.

Lancement depuis ``backend/`` : ``python -m tools.rescore_news``
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import config
from db.repository import SupabaseRepository
from db.supabase_client import get_client
from services.info_scoring import impact_score
from services.news_nlp import ClaudeNewsAnalyzer, NlpUnavailable


def rescore(repo, analyzer, now: datetime) -> dict[str, Counter]:
    since = now - timedelta(days=config.INFO_FENETRE_JOURS)
    summary: dict[str, Counter] = {}
    for action in repo.get_actions():
        articles = repo.get_articles(action["id"], since)
        counts: Counter = Counter()
        if articles:
            try:
                analyses = analyzer.analyze(action["nom"], action["ticker"], articles)
            except NlpUnavailable as error:
                counts["echec"] = len(articles)
                print(f"{action['ticker']} : {error}")
                summary[action["ticker"]] = counts
                continue
            for article, analysis in zip(articles, analyses):
                score = round(impact_score(analysis.sentiment, analysis.annonce), 2) if analysis.pertinent else 50.0
                repo.update_article_score(article["id"], score)
                counts["hors_sujet" if not analysis.pertinent else "positif" if score > 55
                       else "negatif" if score < 45 else "neutre"] += 1
        summary[action["ticker"]] = counts
    return summary


def main() -> int:
    analyzer = ClaudeNewsAnalyzer.from_settings()
    if analyzer is None:
        print("ANTHROPIC_API_KEY absente de backend/.env : rien à faire.")
        return 1
    for ticker, counts in rescore(SupabaseRepository(get_client()), analyzer, datetime.now(timezone.utc)).items():
        print(f"{ticker:7} {dict(counts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
