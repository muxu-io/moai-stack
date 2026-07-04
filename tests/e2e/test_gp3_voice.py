"""GP3 — voice synthesis (runtime voice path).

Resolves Ada's runtime voice spec (authored voxcpm2 + seeded sample → xtts-v2),
POSTs to voice-svc /synthesize requesting WAV, and asserts a valid, non-empty
audio response. Asserts the audio is returned and structurally valid, not its
quality.
"""

import httpx

from helpers.audio import wav_duration_seconds


def test_voice_spec_resolves_to_xtts(ada):
    from persona.fatigue import FatigueLevel
    from persona.voice_spec import resolve_voice_spec
    from persona_core.store_client import StoreClient

    media = StoreClient(ada.cfg.persona_store_url)
    spec = resolve_voice_spec(ada.persona, FatigueLevel.RESTED, media=media)
    assert spec.engine == "xtts-v2"
    assert spec.sample_audio_b64, "expected the seeded voice sample to resolve"


def test_synthesize_returns_valid_wav(ada):
    from persona.fatigue import FatigueLevel
    from persona.voice_spec import resolve_voice_spec
    from persona_core.store_client import StoreClient

    media = StoreClient(ada.cfg.persona_store_url)
    spec = resolve_voice_spec(ada.persona, FatigueLevel.RESTED, media=media)

    body = {
        "text": "Aye, the corridor's dead quiet the night.",
        "engine": spec.engine,
        "language": spec.language,
        "baseline_speed": spec.baseline_speed,
        "fatigue_level": spec.fatigue_level,
        "piper_voice": spec.piper_voice,
        "sample_audio_b64": spec.sample_audio_b64,
        "response_format": "wav",
    }
    r = httpx.post(f"{ada.cfg.voice_svc_url}/synthesize", json=body, timeout=180.0)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("audio/wav")
    assert r.content[:4] == b"RIFF"
    assert wav_duration_seconds(r.content) > 0.0
