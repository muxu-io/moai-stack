"""Create a persona end to end (the authoring path).

The `created` fixture drives persona-create's public API: seed -> generate (LLM,
three phases) -> avatar -> commit. These assertions verify a named persona with a
portrait was authored, landed in persona-store, and is listed by persona-create's
own gallery.
"""


def test_generate_produced_a_named_persona(created):
    assert created.snapshot["skill"] == "ready"
    assert created.snapshot["name"]  # a display name was authored during Conception


def test_avatar_is_webp(created):
    assert created.avatar.status_code == 200
    body = created.avatar.content
    assert body[:4] == b"RIFF" and body[8:12] == b"WEBP"


def test_persona_committed_to_store(created):
    assert created.store.get_persona(created.persona_id).status_code == 200


def test_portrait_media_stored(created):
    r = created.store.get_media(created.persona_id, "portrait")
    assert r.status_code == 200
    assert r.content[:4] == b"RIFF"


def test_persona_listed_in_gallery(created):
    r = created.create.list_personas()
    assert r.status_code == 200
    ids = [card["persona_id"] for card in r.json()["items"]]
    assert created.persona_id in ids
