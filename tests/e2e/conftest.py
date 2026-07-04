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
    if not cfg.persona_file.exists():
        pytest.skip(
            f"persona file not found: {cfg.persona_file}. "
            "Set MOAI_PERSONAS_DIR or check out the monorepo personas."
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
