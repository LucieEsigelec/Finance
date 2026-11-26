"""Analyse des actualités par Claude (D-16) — avec un faux client : aucun appel réel."""

import json
from datetime import timedelta
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from services import news_nlp
from services.news_nlp import Analysis, ClaudeNewsAnalyzer, NlpUnavailable, apply_analysis, parse_response
from services.refresh_service import refresh
from tests.fakes import FakeCollector, FakeRepository
from tests.test_refresh import NOW


def reply(rows, stop_reason="end_turn"):
    text = json.dumps({"articles": rows})
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])


class FakeClient:
    """Répond « sentiment 0,6, annonce » pour chaque article, sauf ceux contenant « homonyme »."""

    def __init__(self, error=None, stop_reason="end_turn"):
        self.calls = []
        self.error = error
        self.stop_reason = stop_reason
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        prompt = kwargs["messages"][0]["content"]
        lines = [line for line in prompt.splitlines() if line.startswith("[")]
        rows = [
            {"index": i, "sentiment": 0.6, "annonce_officielle": True, "concerne_entreprise": "homonyme" not in line}
            for i, line in enumerate(lines)
        ]
        return reply(rows, self.stop_reason)


def articles(n, word="contrat"):
    return [{"titre": f"Dassault Systèmes {word} {i}", "resume": None, "date_pub": NOW - timedelta(hours=i + 1),
             "url": f"https://ex.fr/{word}/{i}", "source": "Presse", "score_impact": 50.0} for i in range(n)]


def test_parse_response_clamps_and_orders():
    text = json.dumps({"articles": [
        {"index": 1, "sentiment": -3, "annonce_officielle": False, "concerne_entreprise": True},
        {"index": 0, "sentiment": 0.4, "annonce_officielle": True, "concerne_entreprise": True},
    ]})
    assert parse_response(text, 2) == [Analysis(0.4, True, True), Analysis(-1.0, False, True)]


@pytest.mark.parametrize("text", ["pas du json", json.dumps({"articles": [{"index": 0, "sentiment": 0.1,
                                  "annonce_officielle": False, "concerne_entreprise": True}]})])
def test_parse_response_rejects_unreadable_or_incomplete_answers(text):
    with pytest.raises(NlpUnavailable):
        parse_response(text, 2)


def test_analyze_sends_one_call_per_40_articles_with_structured_output():
    client = FakeClient()
    analyses = ClaudeNewsAnalyzer(client).analyze("Dassault Systèmes", "DSY.PA", articles(45))
    assert len(analyses) == 45 and len(client.calls) == 2
    call = client.calls[0]
    assert call["model"] == "claude-haiku-5-5"
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert call["output_config"]["effort"] == "low"
    assert "Dassault Systèmes (DSY.PA" in call["messages"][0]["content"]


@pytest.mark.parametrize(
    "client",
    [
        FakeClient(error=anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com"))),
        FakeClient(stop_reason="refusal"),
        FakeClient(stop_reason="max_tokens"),
    ],
)
def test_model_failures_become_nlp_unavailable(client):
    with pytest.raises(NlpUnavailable):
        ClaudeNewsAnalyzer(client).analyze("Dassault Systèmes", "DSY.PA", articles(2))


def test_apply_analysis_uses_spec_formula_and_drops_off_topic_articles():
    kept = apply_analysis(articles(2), [Analysis(0.6, True, True), Analysis(0.9, False, False)])
    assert len(kept) == 1 and kept[0]["score_impact"] == 80.0  # 50 + 50 × 0,6 × 1


def test_without_key_the_lexicon_is_used(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    assert ClaudeNewsAnalyzer.from_settings() is None


def test_refresh_scores_only_new_articles_with_the_model():
    repo = FakeRepository()
    news = {"DSY.PA": articles(3) + articles(1, word="homonyme")}
    client = FakeClient()
    analyzer = ClaudeNewsAnalyzer(client)
    report = refresh(repo, FakeCollector(NOW.date(), articles=news), NOW, analyzer=analyzer)
    dsy = repo.action_by_ticker("DSY.PA")["id"]
    stored = [a for a in repo.articles if a["action_id"] == dsy]
    assert len(stored) == 3 and all(a["score_impact"] == 80.0 for a in stored)  # hors sujet écarté
    assert report["actions"]["DSY.PA"]["analyse"] == "claude"
    calls = len(client.calls)
    refresh(repo, FakeCollector(NOW.date(), articles=news), NOW + timedelta(hours=1), analyzer=analyzer)
    assert len(client.calls) == calls + 1  # « homonyme » n'est pas en base : il est revu, les 3 autres non
    assert client.calls[-1]["messages"][0]["content"].count("\n[") == 1


def test_refresh_falls_back_to_lexicon_when_the_model_fails():
    repo = FakeRepository()
    failing = ClaudeNewsAnalyzer(FakeClient(stop_reason="refusal"))
    news = {"DSY.PA": articles(2)}
    report = refresh(repo, FakeCollector(NOW.date(), articles=news), NOW, analyzer=failing)
    assert any("analyse IA" in e and "lexique" in e for e in report["erreurs"])
    assert len([a for a in repo.articles]) == 2  # articles gardés avec la note du lexique


def test_system_prompt_is_stable_for_caching():
    assert "{" not in news_nlp.SYSTEM_PROMPT  # aucun contenu variable dans le prompt système


def test_rescore_tool_updates_existing_articles():
    from tools.rescore_news import rescore

    repo = FakeRepository()
    dsy = repo.action_by_ticker("DSY.PA")["id"]
    repo.insert_missing_articles(dsy, articles(2) + articles(1, word="homonyme"), NOW - timedelta(days=7))
    summary = rescore(repo, ClaudeNewsAnalyzer(FakeClient()), NOW)
    scores = sorted(a["score_impact"] for a in repo.articles)
    assert scores == [50.0, 80.0, 80.0]  # hors sujet ramené à neutre, rien supprimé
    assert summary["DSY.PA"] == {"positif": 2, "hors_sujet": 1}
