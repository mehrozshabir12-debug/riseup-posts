"""Natural background sound for anime Reels, synthesized (no copyrighted music).
mood -> nature ambience (wind, birds, rain, thunder, crickets) + a soft piano-like melody.
Usage (module): make_audio(path_wav, seconds, mood, seed)
"""
import numpy as np, wave, random
from scipy.signal import butter, lfilter

SR = 44100


def _lp(x, f):
    b, a = butter(2, f / (SR / 2), "low"); return lfilter(b, a, x)


def _bp(x, lo, hi):
    b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], "band"); return lfilter(b, a, x)


def _env(n, att, rel):
    e = np.ones(n); a = int(att * SR); r = int(rel * SR)
    e[:a] = np.linspace(0, 1, a); e[-r:] = np.linspace(1, 0, r); return e


def wind(n, rng, amt=1.0):
    x = _bp(rng.standard_normal(n), 150, 900)
    t = np.arange(n) / SR
    mod = 0.55 + 0.45 * np.sin(2 * np.pi * t / 6.5 + rng.uniform(0, 6)) * np.sin(2 * np.pi * t / 2.3 + 1)
    return x * mod * 0.10 * amt


def leaves(n, rng):
    x = _bp(rng.standard_normal(n), 2500, 7000)
    t = np.arange(n) / SR
    return x * (0.5 + 0.5 * np.sin(2 * np.pi * t / 4.1)) ** 2 * 0.025


def birds(n, rng, count):
    out = np.zeros(n)
    for _ in range(count):
        start = rng.randint(0, n - SR)
        f0 = rng.uniform(2600, 4200); notes = rng.randint(2, 5)
        pos = start
        for k in range(notes):
            dur = rng.uniform(0.06, 0.14); m = int(dur * SR)
            t = np.arange(m) / SR
            f = f0 * (1 + rng.uniform(-0.25, 0.3) * t / dur)
            ph = 2 * np.pi * np.cumsum(f) / SR
            s = np.sin(ph + 0.6 * np.sin(2 * np.pi * 35 * t)) * np.sin(np.pi * t / dur) ** 2
            if pos + m < n:
                out[pos:pos + m] += s * rng.uniform(0.03, 0.06)
            pos += m + int(rng.uniform(0.03, 0.12) * SR)
    return out


def rain(n, rng):
    x = _lp(rng.standard_normal(n), 5000) * 0.06
    drops = np.zeros(n)
    idx = rng.sample(range(n), int(n / SR * 60))
    for i in idx:
        drops[i] = rng.uniform(-1, 1)
    drops = _bp(drops, 1500, 6000) * 0.25
    return x + drops


def thunder(n, rng):
    out = np.zeros(n)
    for _ in range(max(1, n // (SR * 20))):
        st = rng.randint(SR, max(SR + 1, n - 4 * SR)); m = 4 * SR
        r = _lp(np.random.default_rng(rng.randint(0, 9999)).standard_normal(m), 120)
        e = np.exp(-np.arange(m) / (SR * 1.1)) * (1 - np.exp(-np.arange(m) / (SR * 0.08)))
        out[st:st + m] += r * e * 0.6
    return out


def crickets(n, rng):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for _ in range(3):
        f = rng.uniform(4200, 5200); rate = rng.uniform(14, 20)
        chirp = (np.sin(2 * np.pi * rate * t + rng.uniform(0, 6)) > 0.6).astype(float)
        gate = (np.sin(2 * np.pi * t / rng.uniform(1.2, 2.0) + rng.uniform(0, 6)) > -0.2).astype(float)
        out += np.sin(2 * np.pi * f * t) * _lp(chirp * gate, 300) * 0.02
    return out


def piano(n, rng, mood, sad=False):
    """slow gentle arpeggios on major-7 / add9 chords (minor & slower when sad), piano-like decay."""
    out = np.zeros(n)
    root = rng.choice([57, 60, 62, 65])  # A3 C4 D4 F4 (midi)
    prog = rng.choice([[0, 5, 9, 7], [0, 9, 5, 7], [0, 7, 9, 5]])
    shapes = {0: [0, 4, 7, 11, 14], 5: [0, 4, 7, 11, 14], 9: [0, 3, 7, 10, 14], 7: [0, 4, 7, 10, 14]}
    beat = 0.62 if mood != "night" else 0.8
    if sad:
        prog = rng.choice([[0, 8, 3, 10], [0, 5, 8, 7]])
        shapes = {0: [0, 3, 7, 10, 14], 8: [0, 4, 7, 11], 3: [0, 4, 7, 11], 10: [0, 4, 7, 14], 5: [0, 3, 7, 10], 7: [0, 4, 7, 10]}
        beat = 1.0
    pos, i = int(0.5 * SR), 0
    while pos < n - SR:
        deg = prog[(i // 8) % 4]
        notes = shapes[deg]
        midi = root + deg + rng.choice(notes) + rng.choice([0, 0, 12])
        f = 440 * 2 ** ((midi - 69) / 12)
        m = int(3.0 * SR); t = np.arange(m) / SR
        tone = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t))
        tone *= np.exp(-t * 1.6) * (1 - np.exp(-t * 300))
        end = min(n, pos + m)
        out[pos:end] += tone[:end - pos] * 0.05
        if i % 8 == 0:  # soft bass note at chord change
            fb = 440 * 2 ** ((root + deg - 12 - 69) / 12)
            mb = int(4.5 * SR); tb = np.arange(mb) / SR
            bass = np.sin(2 * np.pi * fb * tb) * np.exp(-tb * 0.8) * (1 - np.exp(-tb * 60))
            e2 = min(n, pos + mb); out[pos:e2] += bass[:e2 - pos] * 0.05
        pos += int(beat * SR * rng.choice([1, 1, 1, 2])); i += 1
    # simple reverb
    rev = np.zeros(n)
    for d, g in [(0.031, 0.5), (0.047, 0.4), (0.071, 0.3), (0.113, 0.22), (0.167, 0.15)]:
        k = int(d * SR); rev[k:] += out[:-k] * g
    return out + _lp(rev, 3000) * 0.6


def make_audio(path, seconds, mood, seed=None, sad=False):
    rng = random.Random(seed)
    np.random.seed(rng.randint(0, 2**31 - 1))
    nrng = np.random.default_rng(rng.randint(0, 2**31 - 1))
    n = int(seconds * SR)

    class R:  # numpy normal + python random in one
        standard_normal = staticmethod(lambda k: nrng.standard_normal(k))
        def __getattr__(self, a): return getattr(rng, a)
    r = R()
    mix = piano(n, rng, mood, sad)
    if mood == "rain":
        mix += rain(n, r) + thunder(n, rng) + wind(n, r, 0.6)
    elif mood == "night":
        mix += crickets(n, rng) + wind(n, r, 0.4)
    elif sad:
        mix += wind(n, r, 0.5) + leaves(n, r)
    else:
        mix += wind(n, r) + leaves(n, r) + birds(n, rng, int(seconds / (2.5 if mood in ("day", "spring") else 5)))
    mix *= _env(n, 1.0, 2.0)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.7
    st = np.stack([mix, np.roll(mix, 220) * 0.97], axis=1)
    data = (st * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())
    return path
