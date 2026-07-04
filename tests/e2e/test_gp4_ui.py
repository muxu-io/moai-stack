"""GP4 — UI ↔ inference.

open-webui on :8080 lists ollama-backed models and completes a chat, proving the
UI backend resolves and reaches ollama on the moai network. Independent of
GP2/GP3 — depends only on `cfg`, not the Ada setup.

Two open-webui specifics, both discovered against the running stack:
- Routes need a bearer token even with WEBUI_AUTH=False; we obtain one via
  first-user signup (helpers.openwebui.auth_token), which only works against a
  fresh open-webui-data volume.
- The chat uses open-webui's OpenAI-compatible /api/chat/completions endpoint,
  which correctly returns the answer for a reasoning model. The raw ollama proxy
  (/ollama/api/chat) does NOT forward the `think` flag, so with PERSONA_MODEL
  (a reasoning model) it returns empty content — hence the OpenAI-compat path.

Known external-API risk: open-webui runs the `:main` image (moving target).
"""

import httpx
import pytest

from helpers.openwebui import OpenWebUIAuthError, auth_token


def _model_names(payload: dict) -> list[str]:
    return [m.get("name", "") for m in payload.get("models", [])]


def _matches(name: str, model: str) -> bool:
    base = model.split(":")[0]
    return name == model or name.startswith(model + ":") or name.split(":")[0] == base


@pytest.fixture(scope="session")
def owui_headers(cfg):
    try:
        token = auth_token(cfg.open_webui_url)
    except OpenWebUIAuthError as e:
        pytest.skip(str(e))
    return {"Authorization": f"Bearer {token}"}


def test_open_webui_lists_persona_model(cfg, owui_headers):
    r = httpx.get(f"{cfg.open_webui_url}/ollama/api/tags", headers=owui_headers, timeout=15.0)
    assert r.status_code == 200, r.text
    names = _model_names(r.json())
    assert names, "open-webui returned an empty model list"
    assert any(_matches(n, cfg.persona_model) for n in names), (
        f"PERSONA_MODEL '{cfg.persona_model}' not in {names}"
    )


def test_open_webui_completes_a_chat(cfg, owui_headers):
    # `params: {think: false}` is open-webui's advanced-params passthrough — it
    # forwards `think` to ollama's native flag, disabling reasoning for this
    # request. Without it, PERSONA_MODEL (a reasoning model) spends thousands of
    # tokens in the thinking channel first (35s+ warm, over a minute under GPU
    # contention with GP3's XTTS). With it, the completion is ~1s and direct.
    r = httpx.post(
        f"{cfg.open_webui_url}/api/chat/completions",
        headers=owui_headers,
        json={
            "model": cfg.persona_model,
            "messages": [{"role": "user", "content": "Say hello in exactly one word."}],
            "stream": False,
            "params": {"think": False},
        },
        timeout=60.0,
    )
    assert r.status_code == 200, r.text
    choices = r.json().get("choices") or []
    assert choices, f"no choices in completion: {r.text[:200]}"
    content = choices[0].get("message", {}).get("content", "")
    assert content.strip(), "empty completion from open-webui"
