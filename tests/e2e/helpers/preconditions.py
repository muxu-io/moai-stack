"""Precondition checks: every service healthy and both models pulled.

Returns a list of human-actionable problem strings (empty == all good). The
harness never manages the stack; it fails fast with instructions.
"""

from __future__ import annotations

import httpx

from helpers.config import Config


def _model_present(tags: list[str], model: str) -> bool:
    base = model.split(":")[0]
    return any(t == model or t.startswith(model + ":") or t.split(":")[0] == base for t in tags)


def check_services(cfg: Config) -> list[str]:
    problems: list[str] = []

    def _get(url: str, timeout: float = 5.0) -> httpx.Response:
        return httpx.get(url, timeout=timeout)

    # persona-store (fronts postgres — its health implies the DB is reachable)
    try:
        r = _get(f"{cfg.persona_store_url}/health")
        if not (r.status_code == 200 and r.json().get("ok")):
            problems.append(f"persona-store unhealthy at {cfg.persona_store_url}/health; run `make up`")
    except Exception as e:  # noqa: BLE001 - report any connection failure
        problems.append(f"persona-store unreachable at {cfg.persona_store_url} ({e}); run `make up`")

    # qdrant
    try:
        if _get(f"http://{cfg.qdrant_host}:{cfg.qdrant_port}/healthz").status_code != 200:
            problems.append(f"qdrant unhealthy at {cfg.qdrant_host}:{cfg.qdrant_port}; run `make up`")
    except Exception as e:  # noqa: BLE001
        problems.append(f"qdrant unreachable at {cfg.qdrant_host}:{cfg.qdrant_port} ({e}); run `make up`")

    # voice-svc
    try:
        if _get(f"{cfg.voice_svc_url}/health").status_code != 200:
            problems.append(f"voice-svc unhealthy at {cfg.voice_svc_url}/health; run `make up`")
    except Exception as e:  # noqa: BLE001
        problems.append(f"voice-svc unreachable at {cfg.voice_svc_url} ({e}); run `make up`")

    # open-webui
    try:
        if _get(f"{cfg.open_webui_url}/health").status_code != 200:
            problems.append(f"open-webui unhealthy at {cfg.open_webui_url}/health; run `make up`")
    except Exception as e:  # noqa: BLE001
        problems.append(f"open-webui unreachable at {cfg.open_webui_url} ({e}); run `make up`")

    # ollama + required models
    try:
        r = _get(f"{cfg.ollama_url}/api/tags", timeout=10.0)
        r.raise_for_status()
        tags = [m.get("name", "") for m in r.json().get("models", [])]
        if not _model_present(tags, cfg.persona_model):
            problems.append(f"ollama missing PERSONA_MODEL '{cfg.persona_model}'; run `make pull-model`")
        if not _model_present(tags, cfg.embed_model):
            problems.append(
                f"ollama missing embed model '{cfg.embed_model}'; run "
                f"`docker compose exec ollama ollama pull {cfg.embed_model}`"
            )
    except Exception as e:  # noqa: BLE001
        problems.append(f"ollama unreachable at {cfg.ollama_url} ({e}); run `make up`")

    return problems
