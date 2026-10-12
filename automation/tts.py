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
    mp3 = out_wav[:-4] + ".mp3"
    exe = shutil.which("edge-tts")
    if exe and os.environ.get("RISEUP_TTS") != "gtts":
        for attempt in range(2):
            r = subprocess.run([exe, "--voice", voice, "--text", text, "--write-media", mp3],
                               capture_output=True, text=True, timeout=90)
            if r.returncode == 0 and os.path.exists(mp3) and os.path.getsize(mp3) > 1000:
                _to_wav(mp3, out_wav); os.remove(mp3)
                return out_wav, wav_seconds(out_wav), f"edge-tts:{voice}"
            errors.append(f"edge-tts: {(r.stderr or r.stdout).strip().splitlines()[-1:] or ['exit ' + str(r.returncode)]}")
    elif not exe:
        errors.append("edge-tts not installed")
    # second engine: Google TTS (gTTS), supports Urdu and English
    g = shutil.which("gtts-cli")
    if g:
        tld = "com.pk" if lang == "ur" else "co.uk"
        for attempt in range(2):
            r = subprocess.run([g, text, "-l", lang, "-t", tld, "-o", mp3], capture_output=True, text=True, timeout=90)
            if r.returncode == 0 and os.path.exists(mp3) and os.path.getsize(mp3) > 1000:
                _to_wav(mp3, out_wav); os.remove(mp3)
                return out_wav, wav_seconds(out_wav), f"gtts:{lang}"
            errors.append(f"gtts: {(r.stderr or r.stdout).strip().splitlines()[-1:] or ['exit ' + str(r.returncode)]}")
    else:
        errors.append("gtts not installed")
    if allow_fallback and shutil.which("espeak-ng"):
        subprocess.run(["espeak-ng", "-v", "ur" if lang == "ur" else "en", "-s", "150", "-w", out_wav + ".raw.wav", text],
                       check=True, capture_output=True)
        _to_wav(out_wav + ".raw.wav", out_wav); os.remove(out_wav + ".raw.wav")
        return out_wav, wav_seconds(out_wav), "espeak-ng(fallback)"
    raise RuntimeError("narration failed: " + "; ".join(errors))
