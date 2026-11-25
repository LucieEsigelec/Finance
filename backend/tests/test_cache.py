"""Mémoire courte de l'API (ENF-02) : lectures gardées, effacées après une écriture."""

from decimal import Decimal

from db.cached_repository import MARKET_TTL, PORTFOLIO_TTL, CachedRepository
from tests.fakes import FakeRepository


class CountingRepo(FakeRepository):
    def __init__(self):
        super().__init__()
        self.reads = 0

    def get_actions(self):
        self.reads += 1
        return super().get_actions()

    def get_portfolio(self):
        self.reads += 1
        return super().get_portfolio()


def test_reads_are_cached_until_ttl():
    now = [0.0]
    repo = CountingRepo()
    cached = CachedRepository(repo, clock=lambda: now[0])
    cached.get_actions()
    cached.get_actions()
    assert repo.reads == 1
    now[0] += MARKET_TTL + 1
    cached.get_actions()
    assert repo.reads == 2


def test_transaction_clears_portfolio_but_not_market_data():
    repo = CountingRepo()
    cached = CachedRepository(repo)
    cached.get_actions()
    before = cached.get_portfolio()["cash_disponible"]
    dsy = repo.action_by_ticker("DSY.PA")
    cached.execute_transaction(repo.portfolio["id"], dsy["id"], "ACHAT", 10, {})
    assert cached.get_portfolio()["cash_disponible"] == before - 10 * Decimal(str(dsy["dernier_cours"]))
    reads = repo.reads
    cached.get_actions()
    assert repo.reads == reads  # données de marché toujours en mémoire


def test_refresh_writes_clear_market_data_and_copies_protect_the_cache():
    now = [0.0]
    repo = CountingRepo()
    cached = CachedRepository(repo, clock=lambda: now[0])
    first = cached.get_actions()
    first[0]["nom"] = "modifié par l'appelant"
    assert cached.get_actions()[0]["nom"] != "modifié par l'appelant"
    cached.insert_scores([])
    cached.get_actions()
    assert repo.reads == 2
    now[0] += PORTFOLIO_TTL + 1
    cached.invalidate()
    assert cached.get_history(repo.actions[0]["id"]).empty  # non mis en cache vide abusivement
