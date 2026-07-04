"""GP2 — interactive chat turn (core loop).

Reuses the real persona-cli/persona-core primitives to run one turn end-to-end:
embed → retrieve (Qdrant) → generate (ollama LLM) → write turn-pair (Qdrant) →
persist session_count (persona-store). Asserts the reply, the new turn-pair
record, and the incremented session_count.

PERSONA_MODEL is a reasoning model: with thinking on, run_turn's generate reads
an empty `response` (the whole budget goes to the thinking channel). Rather than
depend on a persona-cli change, we inject a transport that disables thinking at
GenerationClient's own seam (helpers.gen_transport.NoThinkTransport) — so this
runs against a *published* persona-cli. This validates the composition wiring;
the product-level "disable thinking" fix is tracked separately.
"""

import uuid
from datetime import UTC, datetime

from helpers.gen_transport import NoThinkTransport


def test_chat_turn(ada):
    from persona_core.bootstrap import load_persona
    from persona_core.embedding import EmbeddingClient
    from persona_core.qdrant_store import QdrantStore
    from persona_core.store_client import StoreClient
    from persona_core.triggering import TriggerConfig, select_triggered

    from persona.fatigue import FatigueThresholds, derive_fatigue_level
    from persona.generation import GenerationClient, run_turn
    from persona.retrieval import RetrievalConfig, retrieve_relevant
    from persona.scoring import ScoreWeights

    cfg = ada.cfg
    pid = ada.persona_id

    client = StoreClient(cfg.persona_store_url)
    embedder = EmbeddingClient(model=cfg.embed_model)
    store = QdrantStore.http(
        host=cfg.qdrant_host,
        port=cfg.qdrant_port,
        collection=cfg.qdrant_collection,
        vector_size=cfg.vector_size,
        persona_id=pid,
    )
    gen = GenerationClient(
        model=cfg.persona_model, transport=NoThinkTransport(cfg.ollama_url)
    )

    loaded = load_persona(pid, client, embedder)

    # Snapshots
    before_runtime = ada.store.get_runtime(pid)
    before_sessions = before_runtime["session_count"]
    before_turns = ada.qdrant.count(pid, "turn_pair")

    # Session start (mirrors cli.py:164-166)
    session_id = str(uuid.uuid4())
    loaded.runtime_state.session_count += 1
    loaded.runtime_state.last_session_at = datetime.now(tz=UTC)

    working_memory: list = []
    user = "Long shift?"

    # Hot-loop preamble (cli.py:187-204)
    query_vec = embedder.embed(user)
    retrieved = retrieve_relevant(
        store=store,
        query_vector=query_vec,
        config=RetrievalConfig(weights=ScoreWeights()),
        now=datetime.now(tz=UTC),
    )
    triggered = select_triggered(
        persona=loaded.persona,
        user_message=user,
        embedder=embedder,
        config=TriggerConfig(),
    )
    fatigue = derive_fatigue_level(store.count_unconsolidated(), FatigueThresholds())

    try:
        reply = run_turn(
            persona=loaded.persona,
            user_message=user,
            store=store,
            embedder=embedder,
            gen_client=gen,
            session_id=session_id,
            working_memory=working_memory,
            triggered_dims=triggered,
            retrieved=retrieved,
            fatigue_level=fatigue,
            addendum_enabled=False,
            scenario=None,
            runtime_state=loaded.runtime_state,
        )
    finally:
        loaded.runtime_state.save()

    assert reply.strip(), "expected a non-empty reply"
    assert ada.qdrant.count(pid, "turn_pair") == before_turns + 1
    after_runtime = ada.store.get_runtime(pid)
    assert after_runtime["session_count"] == before_sessions + 1
