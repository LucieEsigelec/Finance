"""Socle de l'API : /api/health, CORS, connexion Supabase (sans réseau)."""

import pytest
from fastapi.testclient import TestClient

import config
from config import ConfigError, Settings
from db import supabase_client
from main import create_app

LOCAL = "http://localhost:5173"


@pytest.fixture
def client():
    settings = Settings(supabase_url="", supabase_key="", news_api_key="", cors_origins=(LOCAL,))
    return TestClient(create_app(settings))


def test_health_answers_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["heure_serveur"].endswith("+00:00")


def test_cors_allows_configured_origin(client):
    response = client.get("/api/health", headers={"Origin": LOCAL})
    assert response.headers["access-control-allow-origin"] == LOCAL


def test_cors_rejects_unknown_origin(client):
    response = client.get("/api/health", headers={"Origin": "https://site-inconnu.example"})
    assert "access-control-allow-origin" not in response.headers


def test_supabase_client_requires_env(monkeypatch):
    monkeypatch.setattr(
        supabase_client,
        "load_settings",
        lambda: Settings(supabase_url="", supabase_key="", news_api_key="", cors_origins=()),
    )
    supabase_client.get_client.cache_clear()
    with pytest.raises(ConfigError, match="SUPABASE_URL, SUPABASE_KEY"):
        supabase_client.get_client()
    supabase_client.get_client.cache_clear()


def test_supabase_client_is_created_once(monkeypatch):
    calls = []
    monkeypatch.setattr(
        supabase_client,
        "load_settings",
        lambda: Settings(
            supabase_url="https://exemple.supabase.co", supabase_key="cle", news_api_key="", cors_origins=()
        ),
    )
    monkeypatch.setattr(supabase_client, "create_client", lambda url, key: calls.append(url) or object())
    supabase_client.get_client.cache_clear()
    first = supabase_client.get_client()
    assert supabase_client.get_client() is first
    assert calls == ["https://exemple.supabase.co"]
    supabase_client.get_client.cache_clear()


def test_module_level_app_uses_env_settings():
    import main

    assert main.app.title.startswith("PrimeInvest")
    assert config.load_settings().cors_origins  # au moins une origine par défaut


def test_legacy_import_name_returns_the_shared_client(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(supabase_client, "get_client", lambda: sentinel)
    from db.supabase_client import supabase

    assert supabase is sentinel
    with pytest.raises(AttributeError):
        supabase_client.inconnu  # noqa: B018
