import os
from pathlib import Path

from helpers.config import load_config


def test_defaults(monkeypatch):
    for var in ["PERSONA_STORE_URL", "OLLAMA_URL", "QDRANT_HOST", "QDRANT_PORT",
                "VOICE_SVC_URL", "OPENWEBUI_URL", "PERSONA_MODEL", "EMBED_MODEL",
                "MOAI_PERSONAS_DIR", "TEST_PERSONA_ID", "SCENARIO_ID", "OLLAMA_HOST"]:
        monkeypatch.delenv(var, raising=False)
    cfg = load_config()
    assert cfg.persona_store_url == "http://localhost:7600"
    assert cfg.qdrant_port == 6333
    assert cfg.persona_model == "huihui_ai/qwen3.5-abliterated:9b"
    assert cfg.embed_model == "nomic-embed-text"
    assert cfg.qdrant_collection == "persona_memory"
    assert cfg.vector_size == 768
    assert cfg.test_persona_id == "ada-mcleish-e2e"
    assert cfg.persona_file.name == "ada-mcleish.md"
    assert cfg.scenario_file.name == "shift-cut-corridor.md"
    # load_config points the ollama client lib at the same endpoint
    assert os.environ["OLLAMA_HOST"] == "http://localhost:11434"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("PERSONA_STORE_URL", "http://store:7600/")
    monkeypatch.setenv("QDRANT_PORT", "7000")
    monkeypatch.setenv("MOAI_PERSONAS_DIR", "/data/personas")
    cfg = load_config()
    assert cfg.persona_store_url == "http://store:7600"  # trailing slash stripped
    assert cfg.qdrant_port == 7000
    assert cfg.persona_file == Path("/data/personas/ada-mcleish.md")
