from pathlib import Path

from helpers.scenario_md import parse_scenario_file

REAL = (
    Path(__file__).resolve().parent.parent
    / "fixtures" / "personas" / "ada-mcleish" / "scenarios" / "shift-cut-corridor.md"
)


def test_parses_inline(tmp_path):
    p = tmp_path / "s.md"
    p.write_text(
        "---\n"
        "scenario_id: demo\n"
        'title: "A Title"\n'
        "---\n\n"
        "## Scene\n\n"
        "The corridor is quiet.\n\n"
        "## Interlocutor\n\n"
        "```yaml\n"
        'name: "Mhairi"\n'
        'relation: "colleague"\n'
        "```\n\n"
        "She looks at you.\n"
    )
    sid, title, body = parse_scenario_file(p)
    assert sid == "demo"
    assert title == "A Title"
    assert body["scene"] == "The corridor is quiet."
    assert body["interlocutor"]["name"] == "Mhairi"
    assert body["interlocutor"]["relation"] == "colleague"
    assert body["interlocutor"]["prose"] == "She looks at you."


def test_parses_real_ada_scenario():
    sid, title, body = parse_scenario_file(REAL)
    assert sid == "shift-cut-corridor"
    assert title == "Shift cut, corridor, fluorescent lights"
    assert "fluorescent" in body["scene"].lower()
    assert body["interlocutor"]["name"] == "Mhairi"
    assert body["interlocutor"]["relation"] == "colleague"
    assert body["interlocutor"]["prose"]
