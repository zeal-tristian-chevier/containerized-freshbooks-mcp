from .config import WHISPER_MODEL

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        print(f"[TRANSCRIBER] Loading Whisper model '{WHISPER_MODEL}' (first run downloads ~150MB)...")
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        print("[TRANSCRIBER] Model ready.")
    return _model


def transcribe(audio_path: str) -> str:
    model = _get_model()
    segments, info = model.transcribe(audio_path, beam_size=5, language="en")
    text = " ".join(seg.text.strip() for seg in segments)
    print(f"[TRANSCRIBER] {info.duration:.0f}s audio → {len(text)} chars")
    return text.strip()
