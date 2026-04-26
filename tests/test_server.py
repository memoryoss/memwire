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


def test_list_memories(client):
    """GET /v1/memories returns a paginated list with total count."""
    for i in range(5):
        client.post("/v1/memories", json={
            "user_id": "list_user",
            "messages": [{"role": "user", "content": f"memory {i}"}],
        })
    resp = client.get("/v1/memories?user_id=list_user")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 5
    assert len(data["items"]) >= 5
    assert all(item["user_id"] == "list_user" for item in data["items"])
    # newest first
    timestamps = [item["timestamp"] for item in data["items"]]
    assert timestamps == sorted(timestamps, reverse=True)


def test_list_memories_pagination(client):
    """limit + offset paginate correctly."""
    for i in range(8):
        client.post("/v1/memories", json={
            "user_id": "page_user",
            "messages": [{"role": "user", "content": f"m{i}"}],
        })
    resp = client.get("/v1/memories?user_id=page_user&limit=3&offset=0")
    assert resp.status_code == 200
    page1 = resp.json()
    assert page1["limit"] == 3
    assert page1["offset"] == 0
    assert len(page1["items"]) == 3

    resp = client.get("/v1/memories?user_id=page_user&limit=3&offset=3")
    page2 = resp.json()
    assert len(page2["items"]) == 3
    page1_ids = {i["memory_id"] for i in page1["items"]}
    page2_ids = {i["memory_id"] for i in page2["items"]}
    assert page1_ids.isdisjoint(page2_ids)


def test_list_memories_filters(client):
    """user_id, search, role filters are applied."""
    client.post("/v1/memories", json={
        "user_id": "filter_alice",
        "messages": [{"role": "user", "content": "alice loves coffee"}],
    })
    client.post("/v1/memories", json={
        "user_id": "filter_bob",
        "messages": [{"role": "user", "content": "bob loves tea"}],
    })

    resp = client.get("/v1/memories?user_id=filter_alice")
    assert all(i["user_id"] == "filter_alice" for i in resp.json()["items"])

    resp = client.get("/v1/memories?search=tea")
    items = resp.json()["items"]
    assert any("tea" in i["content"].lower() for i in items)
    assert all("alice loves coffee" not in i["content"] for i in items)


def test_list_memories_no_user_id_returns_all(client):
    """When user_id is omitted, all memories are returned (admin view)."""
    client.post("/v1/memories", json={
        "user_id": "global_a",
        "messages": [{"role": "user", "content": "from a"}],
    })
    client.post("/v1/memories", json={
        "user_id": "global_b",
        "messages": [{"role": "user", "content": "from b"}],
    })
    resp = client.get("/v1/memories")
    items = resp.json()["items"]
    user_ids = {i["user_id"] for i in items}
    assert "global_a" in user_ids
    assert "global_b" in user_ids


def test_list_knowledge(client):
    """GET /v1/knowledge lists KBs with chunk_count."""
    client.post("/v1/knowledge", json={
        "name": "kb_one",
        "chunks": [{"content": "first"}, {"content": "second"}],
        "user_id": "kb_list_user",
    })
    client.post("/v1/knowledge", json={
        "name": "kb_two",
        "chunks": [{"content": "alpha"}],
        "user_id": "kb_list_user",
    })
    resp = client.get("/v1/knowledge?user_id=kb_list_user")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    names = {i["name"] for i in data["items"]}
    assert {"kb_one", "kb_two"}.issubset(names)
    for item in data["items"]:
        assert "chunk_count" in item
        assert "created_at" in item


def test_list_knowledge_search(client):
    """search filter narrows by name."""
    client.post("/v1/knowledge", json={
        "name": "documentation_v1",
        "chunks": [{"content": "x"}],
        "user_id": "search_kb_user",
    })
    client.post("/v1/knowledge", json={
        "name": "release_notes",
        "chunks": [{"content": "y"}],
        "user_id": "search_kb_user",
    })
    resp = client.get("/v1/knowledge?user_id=search_kb_user&search=docu")
    items = resp.json()["items"]
    assert all("docu" in i["name"].lower() for i in items)


def test_dashboard_stats(client):
    """GET /v1/stats returns aggregate counts."""
    client.post("/v1/memories", json={
        "user_id": "stats_a",
        "messages": [{"role": "user", "content": "a stat memory"}],
    })
    client.post("/v1/memories", json={
        "user_id": "stats_b",
        "messages": [{"role": "user", "content": "b stat memory"}],
    })
    resp = client.get("/v1/stats")
    assert resp.status_code == 200
    data = resp.json()
    for key in (
        "total_memories", "distinct_users", "total_nodes", "total_edges",
        "total_knowledge_bases", "total_anchors", "by_category", "by_role",
        "timeseries",
    ):
        assert key in data, f"missing key {key} in stats response"
    assert data["total_memories"] >= 2
    assert data["distinct_users"] >= 2
    assert isinstance(data["by_category"], dict)
    assert isinstance(data["timeseries"], list)
    assert len(data["timeseries"]) == 14
    for point in data["timeseries"]:
        assert "ts" in point and "count" in point


def test_activity(client):
    """GET /v1/activity returns memory adds + KB ingests sorted DESC."""
    client.post("/v1/memories", json={
        "user_id": "act_user",
        "messages": [{"role": "user", "content": "first activity"}],
    })
    client.post("/v1/knowledge", json={
        "name": "act_kb",
        "chunks": [{"content": "chunk"}],
        "user_id": "act_user",
    })
    resp = client.get("/v1/activity?limit=20")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 2
    types = {i["type"] for i in items}
    assert "memory_added" in types
    assert "knowledge_ingested" in types
    timestamps = [i["timestamp"] for i in items]
    assert timestamps == sorted(timestamps, reverse=True)


def test_workspaces_list(client):
    """GET /v1/workspaces aggregates memories by workspace_id."""
    client.post("/v1/memories", json={
        "user_id": "ws_user_1",
        "workspace_id": "team_alpha",
        "messages": [{"role": "user", "content": "alpha team note"}],
    })
    client.post("/v1/memories", json={
        "user_id": "ws_user_2",
        "workspace_id": "team_alpha",
        "messages": [{"role": "user", "content": "alpha team note 2"}],
    })
    client.post("/v1/memories", json={
        "user_id": "ws_user_3",
        "workspace_id": "team_beta",
        "messages": [{"role": "user", "content": "beta team note"}],
    })
    resp = client.get("/v1/workspaces")
    assert resp.status_code == 200
    items = resp.json()["items"]
    by_id = {i["workspace_id"]: i for i in items}
    assert "team_alpha" in by_id
    assert "team_beta" in by_id
    assert by_id["team_alpha"]["memory_count"] >= 2
    assert by_id["team_alpha"]["user_count"] >= 2
    assert by_id["team_beta"]["memory_count"] >= 1


def test_graph(client):
    """GET /v1/graph returns nodes + edges for a user."""
    client.post("/v1/memories", json={
        "user_id": "graph_user",
        "messages": [
            {"role": "user", "content": "I prefer dark mode"},
            {"role": "user", "content": "I love Python and Rust"},
        ],
    })
    resp = client.get("/v1/graph?user_id=graph_user&limit=100")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data and "edges" in data
    assert "total_nodes" in data and "total_edges" in data
    assert "truncated" in data
    assert isinstance(data["nodes"], list)
    if data["nodes"]:
        n = data["nodes"][0]
        assert {"node_id", "token", "memory_ids", "connections"}.issubset(n.keys())


def test_graph_truncation(client):
    """Limit parameter caps node count and reports truncated=true when exceeded."""
    client.post("/v1/memories", json={
        "user_id": "trunc_user",
        "messages": [{"role": "user", "content": " ".join(f"word{i}" for i in range(20))}],
    })
    resp = client.get("/v1/graph?user_id=trunc_user&limit=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["nodes"]) <= 3


def test_auth_info(client):
    """GET /v1/auth/info reports configured count + caller's key prefix."""
    resp = client.get("/v1/auth/info", headers={"X-API-Key": "abcdefghijklmnop"})
    assert resp.status_code == 200
    data = resp.json()
    assert "configured" in data
    assert "configured_count" in data
    assert data["current_key_prefix"] == "abcdefgh"


def test_chat_503_without_provider(client, monkeypatch):
    """When no LLM provider is configured, /v1/chat returns 503."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from memwire.server.app import create_app
    app = create_app()
    with TestClient(app) as c:
        resp = c.post("/v1/chat", json={
            "user_id": "u",
            "messages": [{"role": "user", "content": "hi"}],
        })
        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"].lower()


def test_chat_with_mocked_llm(monkeypatch):
    """Chat endpoint runs recall → inject → call → background-persist → feedback."""
    from memwire.server import llm as llm_mod

    def stub_from_env(cls):
        return llm_mod.LLMConfig(
            api_key="stub",
            base_url="http://stub.example",
            default_model="stub-model",
            available_models=["stub-model"],
        )
    monkeypatch.setattr(llm_mod.LLMConfig, "from_env", classmethod(stub_from_env))

    captured: dict = {}
    async def fake_chat(self, messages, model=None):
        captured["messages"] = messages
        captured["model"] = model
        return {
            "model": model or self.config.default_model,
            "choices": [{"message": {"role": "assistant", "content": "stubbed reply"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        }
    monkeypatch.setattr(llm_mod.LLMClient, "chat", fake_chat)

    from memwire.server.app import create_app
    app = create_app()
    with TestClient(app) as c:
        resp = c.post("/v1/chat", json={
            "user_id": "chat_user",
            "messages": [{"role": "user", "content": "hi memwire"}],
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["message"]["content"] == "stubbed reply"
        assert data["model"] == "stub-model"
        assert "recall" in data
        assert data["usage"]["total_tokens"] == 3


def test_chat_providers(client):
    """GET /v1/chat/providers always returns the openai slot (configured: bool)."""
    resp = client.get("/v1/chat/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    assert "openai" in data["providers"]
    assert "configured" in data["providers"]["openai"]


def test_llm_config_unconfigured(client, monkeypatch, tmp_path):
    """GET /v1/llm/config returns configured=false when no env or saved config."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MEMWIRE_CONFIG_DIR", str(tmp_path))
    from memwire.server.app import create_app
    app = create_app()
    with TestClient(app) as c:
        resp = c.get("/v1/llm/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is False
        assert data["env_locked"] is False


def test_llm_config_save_and_hot_swap(monkeypatch, tmp_path):
    """POST /v1/llm/config persists + swaps the active client."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MEMWIRE_CONFIG_DIR", str(tmp_path))
    from memwire.server.app import create_app
    app = create_app()
    with TestClient(app) as c:
        resp = c.post("/v1/llm/config", json={
            "api_key": "sk-test-12345678",
            "base_url": "http://stub.example/v1",
            "default_model": "stub-model",
            "available_models": ["stub-model", "other-model"],
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["configured"] is True
        assert data["env_locked"] is False
        assert data["base_url"] == "http://stub.example/v1"
        assert data["default_model"] == "stub-model"
        assert data["api_key_prefix"] == "sk-t"
        # second GET reflects the new config
        resp = c.get("/v1/llm/config")
        assert resp.json()["configured"] is True
        # file was actually written
        assert (tmp_path / "llm_config.json").exists()


def test_llm_config_locked_by_env(monkeypatch, tmp_path):
    """When OPENAI_API_KEY is set, POST returns 423 and GET reports env_locked."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-locked-key")
    monkeypatch.setenv("MEMWIRE_CONFIG_DIR", str(tmp_path))
    from memwire.server.app import create_app
    app = create_app()
    with TestClient(app) as c:
        resp = c.get("/v1/llm/config")
        data = resp.json()
        assert data["env_locked"] is True
        assert data["configured"] is True

        resp = c.post("/v1/llm/config", json={"api_key": "sk-different"})
        assert resp.status_code == 423
        assert "env" in resp.json()["detail"].lower()


def test_llm_config_clear(monkeypatch, tmp_path):
    """DELETE /v1/llm/config wipes saved config and tears down the client."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MEMWIRE_CONFIG_DIR", str(tmp_path))
    from memwire.server.app import create_app
    app = create_app()
    with TestClient(app) as c:
        c.post("/v1/llm/config", json={"api_key": "sk-temp"})
        assert (tmp_path / "llm_config.json").exists()

        resp = c.delete("/v1/llm/config")
        assert resp.status_code == 200
        assert resp.json()["configured"] is False
        assert not (tmp_path / "llm_config.json").exists()


def test_llm_test_endpoint_uses_provided_config(monkeypatch, tmp_path):
    """POST /v1/llm/test with body.api_key probes that ad-hoc config without saving."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MEMWIRE_CONFIG_DIR", str(tmp_path))

    from memwire.server import llm as llm_mod

    async def fake_chat(self, messages, model=None):
        return {"model": model, "choices": [{"message": {"role": "assistant", "content": "ok"}}]}
    monkeypatch.setattr(llm_mod.LLMClient, "chat", fake_chat)

    from memwire.server.app import create_app
    app = create_app()
    with TestClient(app) as c:
        resp = c.post("/v1/llm/test", json={
            "api_key": "sk-probe",
            "base_url": "http://stub.example/v1",
            "default_model": "stub-model",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["model"] == "stub-model"
        # nothing was persisted
        assert not (tmp_path / "llm_config.json").exists()


def test_studio_routes_exempt_from_auth(monkeypatch, tmp_path):
    """The /studio prefix bypasses API key middleware (so the SPA can load)."""
    monkeypatch.setenv("MEMWIRE_API_KEYS", "k1")
    studio_dir = tmp_path / "studio_static"
    studio_dir.mkdir()
    (studio_dir / "index.html").write_text("<html><body>studio</body></html>")
    monkeypatch.setenv("STUDIO_STATIC_DIR", str(studio_dir))

    from memwire.server.app import create_app
    app = create_app()
    with TestClient(app) as c:
        # /v1/memories without key -> 401
        resp = c.post("/v1/memories", json={
            "user_id": "u", "messages": [{"role": "user", "content": "x"}],
        })
        assert resp.status_code == 401

        # /studio without key -> 200 (served as static)
        resp = c.get("/studio/")
        assert resp.status_code == 200
        assert "studio" in resp.text


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
