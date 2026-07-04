"""Generate and validate a dependency-free tone WAV for the voice path.

GP3 asserts audio is returned and structurally valid, not its quality, so a
synthesized sine tone is a licence-free, deterministic voice sample.
"""

from __future__ import annotations

import io
import math
import struct
import wave


def tone_wav(seconds: float = 3.0, freq: float = 220.0, framerate: int = 22050) -> bytes:
    """Return a mono 16-bit PCM WAV of a sine tone."""
    n = int(seconds * framerate)
    amp = int(0.3 * 32767)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(framerate)
        frames = bytearray()
        for i in range(n):
            sample = int(amp * math.sin(2 * math.pi * freq * i / framerate))
            frames += struct.pack("<h", sample)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def wav_duration_seconds(data: bytes) -> float:
    """Duration of WAV bytes in seconds. Raises wave.Error on non-WAV input."""
    with wave.open(io.BytesIO(data), "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
    return frames / rate if rate else 0.0
