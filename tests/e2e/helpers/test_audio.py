import io
import wave

import pytest

from helpers.audio import tone_wav, wav_duration_seconds


def test_tone_wav_is_valid_riff():
    data = tone_wav(seconds=1.0, framerate=22050)
    assert data[:4] == b"RIFF"
    assert data[8:12] == b"WAVE"
    with wave.open(io.BytesIO(data), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == 22050
        assert w.getnframes() == 22050


def test_wav_duration_seconds():
    data = tone_wav(seconds=2.0, framerate=16000)
    assert wav_duration_seconds(data) == pytest.approx(2.0, abs=0.01)


def test_wav_duration_rejects_garbage():
    with pytest.raises(wave.Error):
        wav_duration_seconds(b"not a wav")
