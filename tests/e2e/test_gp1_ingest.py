"""GP1 — persona ingest (setup path).

The `ada` fixture performs the ingest; these assertions verify it landed across
persona-store (Postgres), the runtime projection flag, Qdrant (SEEDED_NARRATIVE),
the scenario, and the seeded voice-sample media.
"""


def test_persona_row_exists(ada):
    assert ada.store.get_persona(ada.persona_id).status_code == 200


def test_memory_seeded_true(ada):
    runtime = ada.store.get_runtime(ada.persona_id)
    assert runtime is not None
    assert runtime["memory_seeded"] is True


def test_seeded_narrative_projected_to_qdrant(ada):
    # Ada's markdown carries one trauma (Niamh) → at least one SEEDED_NARRATIVE.
    assert ada.qdrant.count(ada.persona_id, "seeded_narrative") >= 1


def test_scenario_stored(ada):
    r = ada.store.get_scenario(ada.persona_id, ada.cfg.scenario_id)
    assert r.status_code == 200
    assert r.json()["body"]["interlocutor"]["name"] == "Mhairi"


def test_voice_sample_media_stored(ada):
    r = ada.store.get_media(ada.persona_id, "voice-sample.wav")
    assert r.status_code == 200
    assert r.content[:4] == b"RIFF"
