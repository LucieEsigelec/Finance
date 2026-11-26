"""Accès à Supabase : nouvelles tentatives après une coupure de connexion (D-15)."""

import threading
import time
from types import SimpleNamespace

import httpx
import pytest

from db import repository
from db.repository import SupabaseRepository


class FlakyQuery:
    """Requête qui échoue ``failures`` fois avec « Server disconnected » puis réussit."""

    def __init__(self, failures, delay=0.0):
        self.failures = failures
        self.calls = 0
        self.delay = delay
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def execute(self):
        with self._lock:
            self.calls += 1
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(self.delay)
            if self.calls <= self.failures:
                raise httpx.RemoteProtocolError("Server disconnected")
            return SimpleNamespace(data=[{"ok": True}])
        finally:
            with self._lock:
                self.active -= 1


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    monkeypatch.setattr(repository.time, "sleep", lambda s: None)


def test_transient_disconnection_is_retried():
    query = FlakyQuery(failures=2)
    assert SupabaseRepository(client=None)._run(query).data == [{"ok": True}]
    assert query.calls == 3


def test_persistent_disconnection_is_raised_after_3_attempts():
    query = FlakyQuery(failures=5)
    with pytest.raises(httpx.RemoteProtocolError):
        SupabaseRepository(client=None)._run(query, write=True)
    assert query.calls == 3


def test_writes_go_one_at_a_time(monkeypatch):
    monkeypatch.setattr(repository.time, "sleep", time.sleep)  # vraie attente dans execute()
    repo = SupabaseRepository(client=None)
    query = FlakyQuery(failures=0, delay=0.02)
    threads = [threading.Thread(target=repo._run, args=(query,), kwargs={"write": True}) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert query.calls == 5 and query.max_active == 1


def test_local_protocol_error_is_also_retried():
    class LocalFlaky(FlakyQuery):
        def execute(self):
            self.calls += 1
            if self.calls == 1:
                raise httpx.LocalProtocolError("connection closed")
            return SimpleNamespace(data=[])

    query = LocalFlaky(failures=1)
    assert SupabaseRepository(client=None)._run(query, write=True).data == []
    assert query.calls == 2
