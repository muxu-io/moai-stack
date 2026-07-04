"""Environment-driven configuration for the moai-stack e2e harness.

Defaults match the compose port mappings and persona-cli's own env conventions
so the harness talks to the same services the runtime does. Every value is
overridable via the named env var.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Config:
    persona_store_url: str
    ollama_url: str
    qdrant_host: str
    qdrant_port: int
    voice_svc_url: str
    open_webui_url: str
    persona_model: str
    embed_model: str
    qdrant_collection: str
    vector_size: int
    personas_dir: Path
    test_persona_id: str
    scenario_id: str

    @property
    def persona_file(self) -> Path:
        return self.personas_dir / "ada-mcleish.md"

    @property
    def scenario_file(self) -> Path:
        return self.personas_dir / "ada-mcleish" / "scenarios" / f"{self.scenario_id}.md"


def load_config() -> Config:
    personas_dir = Path(
        _env("MOAI_PERSONAS_DIR", str(Path.home() / "moai" / "personas"))
    ).expanduser()
    cfg = Config(
        persona_store_url=_env("PERSONA_STORE_URL", "http://localhost:7600").rstrip("/"),
        ollama_url=_env("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
        qdrant_host=_env("QDRANT_HOST", "localhost"),
        qdrant_port=int(_env("QDRANT_PORT", "6333")),
        voice_svc_url=_env("VOICE_SVC_URL", "http://localhost:7000").rstrip("/"),
        open_webui_url=_env("OPENWEBUI_URL", "http://localhost:8080").rstrip("/"),
        persona_model=_env("PERSONA_MODEL", "huihui_ai/qwen3.5-abliterated:9b"),
        embed_model=_env("EMBED_MODEL", "nomic-embed-text"),
        qdrant_collection=_env("QDRANT_COLLECTION", "persona_memory"),
        vector_size=int(_env("QDRANT_VECTOR_SIZE", "768")),
        personas_dir=personas_dir,
        test_persona_id=_env("TEST_PERSONA_ID", "ada-mcleish-e2e"),
        scenario_id=_env("SCENARIO_ID", "shift-cut-corridor"),
    )
    # The in-process EmbeddingClient/GenerationClient build ollama.Client(), which
    # reads OLLAMA_HOST. Point it at the same endpoint the harness uses (respecting
    # an explicit OLLAMA_HOST if the operator already set one).
    os.environ.setdefault("OLLAMA_HOST", cfg.ollama_url)
    return cfg
