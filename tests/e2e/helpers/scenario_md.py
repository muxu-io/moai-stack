"""Parse a scenario markdown file into the persona-store scenario body shape.

Mirrors what the authoring writer stores: {title, body:{scene, interlocutor}},
where the runtime (persona.cli._scenario_from_store) reads body.scene and
body.interlocutor.{name, relation, prose}.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import frontmatter
import yaml


def parse_scenario_file(path: Path) -> tuple[str, str, dict[str, Any]]:
    """Return (scenario_id, title, body) for a scenario markdown file."""
    post = frontmatter.load(str(path))
    meta = post.metadata
    scenario_id = str(meta.get("scenario_id") or path.stem)
    title = str(meta.get("title") or scenario_id)
    scene = _section(post.content, "Scene")
    interlocutor = _parse_interlocutor(_section(post.content, "Interlocutor"))
    body = {"scene": scene.strip(), "interlocutor": interlocutor}
    return scenario_id, title, body


def _section(content: str, heading: str) -> str:
    m = re.search(
        rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)",
        content,
        re.MULTILINE | re.DOTALL,
    )
    return m.group(1).strip() if m else ""


def _parse_interlocutor(raw: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    ym = re.search(r"```yaml(.*?)```", raw, re.DOTALL)
    if ym:
        loaded = yaml.safe_load(ym.group(1)) or {}
        if isinstance(loaded, dict):
            fields.update({str(k): v for k, v in loaded.items()})
    prose = re.sub(r"```yaml.*?```", "", raw, flags=re.DOTALL).strip()
    if prose:
        fields["prose"] = prose
    return fields
