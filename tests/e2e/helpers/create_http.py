"""Direct httpx helper for driving persona-create's create flow in e2e.

persona-create runs the whole create job synchronously inside POST /api/generate
(it awaits both the avatar and skill tracks before responding), so `generate` is a
long request and the returned snapshot already carries the persona name and ready
track states. Kept minimal — only what the create golden path needs.
"""

from __future__ import annotations

from typing import Any

import httpx


def minimal_seed(vocab: dict[str, Any]) -> dict[str, Any]:
    """Build a valid seed from the served vocabulary superset: the first allowed
    value for every enum field and the low age bound. Measurements are optional and
    left unset (sparse seeds are legal), so the seed stays valid whatever the real
    vocabulary contains."""
    seed: dict[str, Any] = {}
    for field, entries in vocab.items():
        if field in ("age", "measurements"):
            continue
        seed[field] = entries[0]["value"]
    seed["age"] = int(vocab["age"]["min"])
    return seed


class CreateHTTP:
    def __init__(self, base_url: str, *, timeout_s: float = 600.0) -> None:
        # Generation runs the LLM three times; the default timeout is generous.
        self._c = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_s)

    def close(self) -> None:
        self._c.close()

    def health(self) -> dict[str, Any]:
        r = self._c.get("/health")
        r.raise_for_status()
        return r.json()

    def seed_vocabulary(self) -> dict[str, Any]:
        r = self._c.get("/api/seed-vocabulary")
        r.raise_for_status()
        return r.json()

    def generate(self, seed: dict[str, Any]) -> httpx.Response:
        return self._c.post("/api/generate", json=seed)

    def get_status(self, job_id: str) -> httpx.Response:
        return self._c.get(f"/api/generate/{job_id}")

    def get_avatar(self, job_id: str) -> httpx.Response:
        return self._c.get(f"/api/generate/{job_id}/avatar")

    def commit(self, job_id: str) -> httpx.Response:
        return self._c.post(f"/api/generate/{job_id}/commit")

    def list_personas(self) -> httpx.Response:
        return self._c.get("/api/personas")
