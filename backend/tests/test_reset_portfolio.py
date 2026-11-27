"""Outil de remise à zéro du portefeuille (D-23), testé sur la fausse base."""

from datetime import date
from decimal import Decimal

import db.repository
import db.supabase_client
from tests.fakes import FakeRepository
from tools import reset_portfolio


def _repo_with_trades():
    repo = FakeRepository()
    dsy = repo.action_by_ticker("DSY.PA")["id"]
    repo.execute_transaction(repo.portfolio["id"], dsy, "ACHAT", 100, {})
    repo.update_portfolio_profile(repo.portfolio["id"], "DYNAMIQUE", "M. Dupont")
    return repo


def test_reset_clears_trades_and_restores_cash():
    repo = _repo_with_trades()
    assert repo.portfolio["cash_disponible"] < Decimal("500000")
    assert reset_portfolio.reset(repo, date(2026, 11, 27)) == 1
    assert repo.get_transactions(repo.portfolio["id"]) == []
    assert repo.portfolio["cash_disponible"] == Decimal("500000.00")
    assert repo.portfolio["val_semaine_prec"] == Decimal("500000.00")
    assert repo.portfolio["date_ref_semaine"] == date(2026, 11, 23)  # lundi de la semaine
    assert repo.portfolio["profil_risque"] == "DYNAMIQUE"  # profil gardé par défaut


def test_reset_can_clear_profile():
    repo = _repo_with_trades()
    reset_portfolio.reset(repo, date(2026, 11, 27), clear_profile=True)
    assert repo.portfolio["profil_risque"] is None and repo.portfolio["nom_client"] is None


def _patch(monkeypatch, repo, answer):
    monkeypatch.setattr(db.supabase_client, "get_client", lambda: None)
    monkeypatch.setattr(db.repository, "SupabaseRepository", lambda client: repo)
    monkeypatch.setattr("builtins.input", lambda prompt: answer)


def test_main_without_confirmation_changes_nothing(monkeypatch, capsys):
    repo = _repo_with_trades()
    _patch(monkeypatch, repo, "non")
    assert reset_portfolio.main([]) == 1
    assert len(repo.get_transactions(repo.portfolio["id"])) == 1
    assert "Annulé" in capsys.readouterr().out


def test_main_with_confirmation_resets(monkeypatch, capsys):
    repo = _repo_with_trades()
    _patch(monkeypatch, repo, "RESET")
    assert reset_portfolio.main([]) == 0
    assert repo.get_transactions(repo.portfolio["id"]) == []
    out = capsys.readouterr().out
    assert "DSY.PA 100" in out and "1 opération(s) supprimée(s)" in out
