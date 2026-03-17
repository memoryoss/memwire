"""MemWire SDK client — thin HTTP wrapper around the MemWire REST API."""

from typing import Optional

import httpx

from .types import MemoryRecord, RecallResult, RecallPath, KnowledgeChunk, SearchResult


class MemWireClient:
    """Client for the MemWire REST API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
        )

    def _request(self, method: str, path: str, **kwargs) -> dict | list:
        resp = self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def add(
        self,
        user_id: str,
        messages: list[dict[str, str]],
        *,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> list[MemoryRecord]:
        data = self._request("POST", "/v1/memories", json={
            "user_id": user_id,
            "messages": messages,
            "agent_id": agent_id,
            "app_id": app_id,
            "workspace_id": workspace_id,
        })
        return [MemoryRecord(**r) for r in data]

    def recall(
        self,
        query: str,
        user_id: str,
        *,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> RecallResult:
        data = self._request("POST", "/v1/memories/recall", json={
            "query": query,
            "user_id": user_id,
            "agent_id": agent_id,
            "app_id": app_id,
            "workspace_id": workspace_id,
        })
        return self._parse_recall(data)

    def search(
        self,
        query: str,
        user_id: str,
        *,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        data = self._request("POST", "/v1/memories/search", json={
            "query": query,
            "user_id": user_id,
            "agent_id": agent_id,
            "app_id": app_id,
            "workspace_id": workspace_id,
            "category": category,
            "limit": limit,
        })
        return [
            SearchResult(memory=MemoryRecord(**r["memory"]), score=r["score"])
            for r in data
        ]

    def feedback(
        self,
        assistant_response: str,
        user_id: str,
        *,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> dict:
        return self._request("POST", "/v1/memories/feedback", json={
            "assistant_response": assistant_response,
            "user_id": user_id,
            "agent_id": agent_id,
            "app_id": app_id,
            "workspace_id": workspace_id,
        })

    def add_knowledge(
        self,
        name: str,
        chunks: list[dict],
        user_id: str,
        *,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> str:
        data = self._request("POST", "/v1/knowledge", json={
            "name": name,
            "chunks": chunks,
            "user_id": user_id,
            "agent_id": agent_id,
            "app_id": app_id,
            "workspace_id": workspace_id,
        })
        return data["kb_id"]

    def search_knowledge(
        self,
        query: str,
        user_id: str,
        *,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        limit: int = 5,
    ) -> list[KnowledgeChunk]:
        data = self._request("POST", "/v1/knowledge/search", json={
            "query": query,
            "user_id": user_id,
            "agent_id": agent_id,
            "app_id": app_id,
            "workspace_id": workspace_id,
            "limit": limit,
        })
        return [KnowledgeChunk(**c) for c in data]

    def delete_knowledge(self, kb_id: str, user_id: str) -> None:
        self._request("DELETE", f"/v1/knowledge/{kb_id}", params={"user_id": user_id})

    def add_category(
        self,
        name: str,
        text: str,
        user_id: str,
        *,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> None:
        self._request("POST", "/v1/categories", json={
            "name": name,
            "text": text,
            "user_id": user_id,
            "app_id": app_id,
            "workspace_id": workspace_id,
        })

    def get_stats(
        self,
        user_id: str,
        *,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> dict:
        return self._request("POST", "/v1/stats", json={
            "user_id": user_id,
            "agent_id": agent_id,
            "app_id": app_id,
            "workspace_id": workspace_id,
        })

    def health(self) -> dict:
        return self._request("GET", "/health")

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @staticmethod
    def _parse_recall(data: dict) -> RecallResult:
        supporting = [
            RecallPath(
                tokens=p["tokens"],
                score=p["score"],
                memories=[MemoryRecord(**m) for m in p["memories"]],
            )
            for p in data.get("supporting", [])
        ]
        conflicting = [
            RecallPath(
                tokens=p["tokens"],
                score=p["score"],
                memories=[MemoryRecord(**m) for m in p["memories"]],
            )
            for p in data.get("conflicting", [])
        ]
        knowledge = [KnowledgeChunk(**k) for k in data.get("knowledge", [])]
        return RecallResult(
            query=data["query"],
            supporting=supporting,
            conflicting=conflicting,
            knowledge=knowledge,
            formatted=data.get("formatted", ""),
            has_conflicts=data.get("has_conflicts", False),
        )
