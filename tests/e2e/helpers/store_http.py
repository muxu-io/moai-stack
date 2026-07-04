"""Direct httpx helpers for persona-store writes/reads used in e2e setup.

persona-core's StoreClient is read-only; the design specifies ingest is done
directly over persona-store HTTP. Kept minimal — only what the harness needs.
"""

from __future__ import annotations

from typing import Any

import httpx


class StoreHTTP:
    def __init__(self, base_url: str, *, timeout_s: float = 30.0) -> None:
        self._c = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_s)

    def close(self) -> None:
        self._c.close()

    def health(self) -> dict[str, Any]:
        r = self._c.get("/health")
        r.raise_for_status()
        return r.json()

    def post_persona(
        self,
        persona_id: str,
        definition: dict[str, Any],
        *,
        spec_version: int = 1,
        tags: list[str] | None = None,
    ) -> None:
        r = self._c.post(
            "/personas",
            json={
                "persona_id": persona_id,
                "spec_version": spec_version,
                "definition": definition,
                "tags": tags or [],
            },
        )
        r.raise_for_status()

    def get_persona(self, persona_id: str) -> httpx.Response:
        return self._c.get(f"/personas/{persona_id}")

    def get_runtime(self, persona_id: str) -> dict[str, Any] | None:
        r = self._c.get(f"/personas/{persona_id}/runtime")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def put_scenario(
        self, persona_id: str, scenario_id: str, *, title: str, body: dict[str, Any]
    ) -> None:
        r = self._c.put(
            f"/personas/{persona_id}/scenarios/{scenario_id}",
            json={"title": title, "body": body},
        )
        r.raise_for_status()

    def get_scenario(self, persona_id: str, scenario_id: str) -> httpx.Response:
        return self._c.get(f"/personas/{persona_id}/scenarios/{scenario_id}")

    def put_media(self, persona_id: str, name: str, data: bytes) -> None:
        r = self._c.put(f"/personas/{persona_id}/media/{name}", content=data)
        r.raise_for_status()

    def get_media(self, persona_id: str, name: str) -> httpx.Response:
        return self._c.get(f"/personas/{persona_id}/media/{name}")

    def delete_persona(self, persona_id: str) -> None:
        r = self._c.delete(f"/personas/{persona_id}")
        if r.status_code not in (204, 404):
            r.raise_for_status()
