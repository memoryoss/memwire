"""Tests for the REST API server."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from memwire.server.app import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_add_and_recall(client):
    resp = client.post("/v1/memories", json={
        "user_id": "test_user",
        "messages": [
            {"role": "user", "content": "I prefer dark mode"},
            {"role": "user", "content": "My favorite language is Python"},
        ],
    })
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 2
    assert records[0]["content"] == "I prefer dark mode"

    resp = client.post("/v1/memories/recall", json={
        "query": "What are the user preferences?",
        "user_id": "test_user",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "What are the user preferences?"
    assert isinstance(data["supporting"], list)
    assert isinstance(data["formatted"], str)


def test_add_rejects_invalid_messages(client):
    resp = client.post("/v1/memories", json={
        "user_id": "u",
        "messages": [{"bad_key": "no role or content"}],
    })
    assert resp.status_code == 422


def test_search(client):
    client.post("/v1/memories", json={
        "user_id": "search_user",
        "messages": [{"role": "user", "content": "I love hiking in the mountains"}],
    })
    resp = client.post("/v1/memories/search", json={
        "query": "outdoor activities",
        "user_id": "search_user",
    })
    assert resp.status_code == 200


def test_feedback(client):
    client.post("/v1/memories", json={
        "user_id": "fb_user",
        "messages": [{"role": "user", "content": "I like coffee"}],
    })
    client.post("/v1/memories/recall", json={
        "query": "beverages",
        "user_id": "fb_user",
    })
    resp = client.post("/v1/memories/feedback", json={
        "assistant_response": "You mentioned you like coffee",
        "user_id": "fb_user",
    })
    assert resp.status_code == 200
    assert "strengthened" in resp.json()


def test_knowledge_lifecycle(client):
    resp = client.post("/v1/knowledge", json={
        "name": "test_kb",
        "chunks": [{"content": "The sky is blue"}, {"content": "Water is wet"}],
        "user_id": "kb_user",
    })
    assert resp.status_code == 200
    kb_id = resp.json()["kb_id"]

    resp = client.post("/v1/knowledge/search", json={
        "query": "sky color",
        "user_id": "kb_user",
    })
    assert resp.status_code == 200

    resp = client.delete(f"/v1/knowledge/{kb_id}?user_id=kb_user")
    assert resp.status_code == 200


def test_knowledge_delete_wrong_user(client):
    resp = client.post("/v1/knowledge", json={
        "name": "owned_kb",
        "chunks": [{"content": "secret data"}],
        "user_id": "owner",
    })
    kb_id = resp.json()["kb_id"]

    resp = client.delete(f"/v1/knowledge/{kb_id}?user_id=attacker")
    assert resp.status_code == 404


def test_knowledge_rejects_invalid_chunks(client):
    resp = client.post("/v1/knowledge", json={
        "name": "bad_kb",
        "chunks": [{"no_content_key": "oops"}],
        "user_id": "u",
    })
    assert resp.status_code == 422


def test_categories(client):
    resp = client.post("/v1/categories", json={
        "name": "custom_category",
        "text": "This is a test category",
        "user_id": "category_user",
    })
    assert resp.status_code == 200


def test_stats(client):
    client.post("/v1/memories", json={
        "user_id": "stats_user",
        "messages": [{"role": "user", "content": "test memory"}],
    })
    resp = client.post("/v1/stats", json={"user_id": "stats_user"})
    assert resp.status_code == 200
    data = resp.json()
    assert "memories" in data
    assert "nodes" in data


def test_api_key_auth(monkeypatch):
    """Test that API key middleware works when keys are configured."""
    monkeypatch.setenv("MEMWIRE_API_KEYS", "test-key-123,test-key-456")
    from memwire.server.app import create_app
    app = create_app()
    with TestClient(app) as c:
        # no key -> 401
        resp = c.post("/v1/memories", json={
            "user_id": "u", "messages": [{"role": "user", "content": "hi"}],
        })
        assert resp.status_code == 401

        # wrong key -> 401
        resp = c.post("/v1/memories", json={
            "user_id": "u", "messages": [{"role": "user", "content": "hi"}],
        }, headers={"X-API-Key": "wrong"})
        assert resp.status_code == 401

        # valid key -> 200
        resp = c.post("/v1/memories", json={
            "user_id": "u", "messages": [{"role": "user", "content": "hi"}],
        }, headers={"X-API-Key": "test-key-123"})
        assert resp.status_code == 200

        # health is exempt
        resp = c.get("/health")
        assert resp.status_code == 200
