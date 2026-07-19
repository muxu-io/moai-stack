"""Session fixtures for the moai-stack e2e harness.

`cfg` loads env-driven config. `ada` performs the GP1 ingest (parse Ada's
markdown → POST persona → PUT scenario → PUT tone voice-sample) under a
dedicated test persona_id, yields a handle, and always tears down via a
finalizer. Teardown deletes the persona (Postgres cascade) and purges Qdrant
records directly; media has no delete route, so the tone blob is overwritten in
place on each run under the stable id (never accumulates).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from helpers.audio import tone_wav
from helpers.config import load_config
from helpers.create_http import CreateHTTP, minimal_seed
from helpers.qdrant_admin import QdrantAdmin
from helpers.scenario_md import parse_scenario_file
from helpers.store_http import StoreHTTP


@pytest.fixture(scope="session")
def cfg():
    return load_config()


def _purge(store: StoreHTTP, qa: QdrantAdmin, persona_id: str) -> None:
    store.delete_persona(persona_id)
    qa.purge(persona_id)


@pytest.fixture(scope="session")
def ada(cfg):
    assert cfg.persona_file.exists(), (
        f"persona fixture not found: {cfg.persona_file}. "
        "It is vendored with the suite; unset MOAI_PERSONAS_DIR to use it."
    )

    # Reuse the real parser/serializer so the POSTed definition matches runtime.
    from persona_core.parser import parse_persona_file
    from persona_core.serialization import persona_to_definition
    from persona_core.store_client import StoreClient

    store = StoreHTTP(cfg.persona_store_url)
    qa = QdrantAdmin(cfg.qdrant_host, cfg.qdrant_port, cfg.qdrant_collection)
    pid = cfg.test_persona_id

    # Stable id → clean any residue from a prior aborted run before ingesting.
    _purge(store, qa, pid)

    parsed = parse_persona_file(cfg.persona_file)
    definition = persona_to_definition(parsed)
    store.post_persona(pid, definition, spec_version=parsed.spec_version)

    scen_id, title, body = parse_scenario_file(cfg.scenario_file)
    store.put_scenario(pid, cfg.scenario_id, title=title, body=body)

    store.put_media(pid, "voice-sample.wav", tone_wav())

    # Expose the store-canonical persona: its persona_id is the TEST id, so
    # voice-spec media resolution (get_media(persona.persona_id, ...)) hits the
    # blob we just seeded. The file-parsed object keeps the original id and would
    # miss. This mirrors the runtime, which loads the persona from the store.
    persona = StoreClient(cfg.persona_store_url).get_persona(pid)

    handle = SimpleNamespace(
        persona_id=pid,
        persona=persona,
        cfg=cfg,
        store=store,
        qdrant=qa,
    )
    try:
        yield handle
    finally:
        _purge(store, qa, pid)
        store.close()


@pytest.fixture(scope="session")
def image_gen_ready(cfg):
    """Warm image-gen before the create flow: render once for the model persona-create
    will use, polling through the `503 model_loading` responses so the create test's own
    first render is fast and doesn't pay the cold-start (model download) latency."""
    import time

    import httpx

    payload = {
        "prompt": "studio portrait, plain background",
        "negative_prompt": "lowres, watermark, text",
        "width": 768,
        "height": 1024,
        "safe": False,
    }
    if cfg.image_gen_model:
        payload["model_id"] = cfg.image_gen_model

    budget_s = 1800.0  # cold model download (~GB) + first render
    deadline = time.monotonic() + budget_s
    with httpx.Client(base_url=cfg.image_gen_url, timeout=budget_s) as c:
        while True:
            r = c.post("/render", json=payload)
            if r.status_code == 200:
                return
            if r.status_code == 503 and time.monotonic() < deadline:
                time.sleep(5)  # model still loading; retry shortly
                continue
            pytest.fail(
                f"image-gen not ready ({cfg.image_gen_model or 'default'}): "
                f"{r.status_code} {r.text[:200]}"
            )


@pytest.fixture(scope="session")
def created(cfg, image_gen_ready):
    """Create-flow setup: drive persona-create's create flow end to end, yield a handle.

    The seed is derived from the live vocabulary so it stays valid whatever the
    skills tree contains. generate() blocks until the LLM finishes all three
    phases; the avatar is fetched pre-commit, then the persona is committed to the
    store. Always tears down by deleting the committed persona.
    """
    cc = CreateHTTP(cfg.persona_create_url)
    store = StoreHTTP(cfg.persona_store_url)

    seed = minimal_seed(cc.seed_vocabulary())
    snapshot = cc.generate(seed)
    snapshot.raise_for_status()
    job = snapshot.json()
    job_id = job["id"]

    avatar = cc.get_avatar(job_id)
    commit = cc.commit(job_id)
    commit.raise_for_status()
    persona_id = commit.json()["persona_id"]

    handle = SimpleNamespace(
        persona_id=persona_id,
        job_id=job_id,
        snapshot=job,
        avatar=avatar,
        cfg=cfg,
        create=cc,
        store=store,
    )
    try:
        yield handle
    finally:
        store.delete_persona(persona_id)
        store.close()
        cc.close()
