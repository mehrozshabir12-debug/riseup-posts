"""Text-to-speech for narrated Reels.

Primary engine: edge-tts (Microsoft neural voices; needs internet - works on GitHub Actions runners).
Fallback:       espeak-ng (offline, robotic) - only when allow_fallback is True.
Test mode:      RISEUP_TTS=silent makes timed silence (for offline tests only, never for publishing).
Returns (wav_path, seconds, engine).
"""
import os, subprocess, shutil, wave
import numpy as np

SR = 44100
DEFAULT_VOICE = {"ur": "ur-PK-AsadNeural", "en": "en-GB-RyanNeural"}


def _to_wav(src, dst):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", str(SR), dst], check=True)


def wav_seconds(path):
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def read_wav(path):
    with wave.open(path) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return a


def speak(text, out_wav, lang="ur", voice=None, allow_fallback=False):
    voice = voice or DEFAULT_VOICE.get(lang, DEFAULT_VOICE["ur"])
    if os.environ.get("RISEUP_TTS") == "silent":
        n = int(SR * max(1.5, len(text.split()) / 2.5))
        with wave.open(out_wav, "w") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.zeros(n)).astype(np.int16).tobytes())
        return out_wav, wav_seconds(out_wav), "silent-test"
    errors = []
    exe = shutil.which("edge-tts")
    if exe:
        mp3 = out_wav[:-4] + ".mp3"
        for attempt in range(3):
            try:
                subprocess.run([exe, "--voice", voice, "--rate=+4%", "--text", text, "--write-media", mp3],
                               check=True, capture_output=True, timeout=90)
                _to_wav(mp3, out_wav); os.remove(mp3)
                return out_wav, wav_seconds(out_wav), f"edge-tts:{voice}"
            except Exception as e:  # network hiccup -> retry
                errors.append(f"edge-tts attempt {attempt + 1}: {e}")
    else:
        errors.append("edge-tts not installed")
    if allow_fallback and shutil.which("espeak-ng"):
        subprocess.run(["espeak-ng", "-v", "ur" if lang == "ur" else "en", "-s", "150", "-w", out_wav + ".raw.wav", text],
                       check=True, capture_output=True)
        _to_wav(out_wav + ".raw.wav", out_wav); os.remove(out_wav + ".raw.wav")
        return out_wav, wav_seconds(out_wav), "espeak-ng(fallback)"
    raise RuntimeError("narration failed: " + "; ".join(errors))
