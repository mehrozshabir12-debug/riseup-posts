"""Copyright-safe audio for narrated news Reels, synthesised from scratch (no samples).

breaking_sting(): ~2.2 s 'breaking news' hit (riser + three punchy hits + bright tone)
news_bed():       soft pulsing news bed to sit quietly under the narration
"""
import numpy as np

SR = 44100


def _env(n, a, r):
    e = np.ones(n)
    a, r = min(n, max(1, int(a * SR))), min(n, max(1, int(r * SR)))
    e[:a] = np.linspace(0, 1, a)
    e[-r:] *= np.linspace(1, 0, r)
    return e


def _hit(f0, dur, rng, noise=0.25):
    n = int(dur * SR); t = np.arange(n) / SR
    pitch = f0 * (1 + 1.5 * np.exp(-t * 30))           # pitch drop = punch
    body = np.sin(2 * np.pi * np.cumsum(pitch) / SR)
    nz = rng.standard_normal(n) * np.exp(-t * 40) * noise
    return (body * np.exp(-t * 6) + nz) * _env(n, 0.002, 0.05)


def _tone(freqs, dur, decay=2.5):
    n = int(dur * SR); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t) / (k + 1) for k, f in enumerate(freqs))
    return s * np.exp(-t * decay) * _env(n, 0.005, 0.2)


def breaking_sting(seed=0):
    rng = np.random.default_rng(seed)
    out = np.zeros(int(2.3 * SR))
    # riser 0-0.6 s
    n = int(0.6 * SR); t = np.arange(n) / SR
    f = 200 + 900 * (t / t[-1]) ** 2
    riser = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.linspace(0, 0.35, n)
    riser += rng.standard_normal(n) * np.linspace(0, 0.08, n)
    out[:n] += riser
    # three hits
    for k, at in enumerate((0.6, 0.85, 1.1)):
        h = _hit(70 if k < 2 else 55, 0.7, rng)
        i = int(at * SR); out[i:i + len(h)] += h[: len(out) - i] * (0.9 if k < 2 else 1.0)
    # bright 'news' chord on the last hit
    ch = _tone([523.25, 659.25, 783.99, 1046.5], 1.2, 2.2) * 0.35
    i = int(1.1 * SR); out[i:i + len(ch)] += ch[: len(out) - i]
    return out / (np.abs(out).max() + 1e-9) * 0.9


def news_bed(seconds, seed=0):
    rng = np.random.default_rng(seed + 7)
    n = int(seconds * SR); t = np.arange(n) / SR
    root = rng.choice([110.0, 98.0, 123.47])
    pad = sum(np.sin(2 * np.pi * root * m * t + rng.uniform(0, 6)) for m in (1, 1.5, 2, 3)) / 4
    pad *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.08 * t)
    bpm = 100; beat = 60 / bpm
    pulse = np.zeros(n)
    tick = _tone([880.0, 1320.0], 0.12, 30)
    kick = _hit(60, 0.25, rng, noise=0.05)
    k = 0
    while k * beat < seconds:
        i = int(k * beat * SR)
        src = kick if k % 2 == 0 else tick * 0.5
        seg = src[: max(0, n - i)]
        pulse[i:i + len(seg)] += seg
        k += 1
    bed = pad * 0.5 + pulse * 0.35
    bed *= _env(n, 1.0, 1.5)
    return bed / (np.abs(bed).max() + 1e-9)
