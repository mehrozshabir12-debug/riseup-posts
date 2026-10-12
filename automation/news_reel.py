"""Narrated single-story news Reel (1080x1920, max 60 s) built ONLY from approved template parts.

Look = the approved anime-Reel layout (template/make_anime_reel.py): same black fade, logo + wordmark,
footer icons (no X), yellow bar + big white headline + yellow highlights. The background changes per
segment using the approved topic scenes (template/scenes.py, different seeds / related scenes), with a
slow zoom and cross-fades. The Reel opens on the approved news card (the -story.jpg = Reel cover).

Audio: synthesised breaking-news sting + soft news bed (automation/news_audio.py) + TTS narration
(automation/tts.py), one narration clip per segment so the text and voice stay in sync.

Usage (normally called by process_request.py):
  python3 automation/news_reel.py reel_cfg.json story.jpg out.mp4
"""
import json, os, sys, subprocess, tempfile, wave
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "template"))
sys.path.insert(0, HERE)
import make_anime_reel as AR   # approved text layers + static branding layer
import scenes                  # approved topic scenes
import news_audio, tts

W, H, FPS = 1080, 1920, 30
BG_H = 1150            # scene area (fades into black from y=830 like the post)
COVER_S = 2.2          # approved card shown first (sting plays)
FADE = 0.45
XFADE = 0.5
MAX_S = 60.0


def _cover_fit(img, w, h):
    r = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    l = (img.width - w) // 2; t = max(0, (img.height - h) // 3)
    return img.crop((l, t, l + w, t + h))


def _zoom(img, z, w, h):
    cw, ch = int(img.width / z), int(img.height / z)
    l, t = (img.width - cw) // 2, (img.height - ch) // 2
    return img.crop((l, t, l + cw, t + ch)).resize((w, h), Image.BILINEAR)


def reel_text_cfg(req):
    card, reel = req["card"], req.get("reel") or {}
    en = req.get("language") == "English"
    return {
        "line1": reel.get("line1") or card["head1"],
        "line2": reel.get("line2") or (card.get("head2_hl", "") + " " + card.get("head2", "")).strip(),
        "sub": reel.get("sub") or card.get("desc", ""),
        "sub_hl": reel.get("sub_hl", ""),
        "tag": reel.get("tag") or card.get("kicker", ""),
        "question": reel["outro_question"],
        "source": card.get("source", ""),
        "outro_label": reel.get("outro_label") or ("Your view?" if en else "Aap ki raye?"),
        "outro_cta": reel.get("outro_cta") or ("Comment below and **Follow us**" if en else "Comment mein batayein aur **Follow karein**"),
    }


def build(req, story_jpg, out_mp4, seed=None, allow_fallback_voice=False):
    reel = req["reel"]
    seed = seed if seed is not None else (req["card"].get("seed") or 12345)
    lang = reel.get("narration_lang") or ("en" if req.get("language") == "English" else "ur")
    voice = reel.get("voice")
    tcfg = reel_text_cfg(req)
    segs_in = reel["segments"]
    n = len(segs_in)

    tmp = tempfile.mkdtemp(prefix="reel_")
    # ---- narration, one clip per segment ----
    spoken = [reel["intro_voice"]] + [s["voice"] for s in segs_in] + [reel.get("outro_voice") or reel["outro_question"]]
    clips, engine = [], None
    for i, text in enumerate(spoken):
        p, secs, eng = tts.speak(text, os.path.join(tmp, f"v{i}.wav"), lang, voice, allow_fallback_voice)
        clips.append((p, secs)); engine = eng
    layers = [("intro", AR.intro_layer(tcfg))] + \
             [("para", AR.para_layer(tcfg, s["text"], i, n)) for i, s in enumerate(segs_in)] + \
             [("outro", AR.outro_layer(tcfg))]
    segs = [("cover", COVER_S, None, None)]
    for (kind, layer), (clip, secs) in zip(layers, clips):
        segs.append((kind, max(3.5, secs + (1.1 if kind == "outro" else 0.75)), layer, clip))
    total = sum(s[1] for s in segs)
    if total > MAX_S:
        raise ValueError(f"narrated Reel would be {total:.1f} s (max {MAX_S:.0f} s): shorten the voice lines")

    # ---- backgrounds: approved scenes, changing per segment ----
    scene_list = reel.get("scenes") or [req["card"]["scene"]]
    bgs = []
    for i in range(len(segs) - 1):
        sc = scene_list[i % len(scene_list)]
        img = scenes.render(sc, (seed + 7919 * (i + 1)) % (10 ** 9))
        bgs.append(_cover_fit(img, int(W * 1.08), int(BG_H * 1.08)))
    static = AR.static_layer()
    story = Image.open(story_jpg).convert("RGB").resize((W, H), Image.LANCZOS)
    story_big = story.resize((int(W * 1.05), int(H * 1.05)), Image.LANCZOS)

    # ---- audio mix ----
    SR = news_audio.SR
    N = int(total * SR)
    mix = news_audio.news_bed(total, seed) * 0.06
    st = news_audio.breaking_sting(seed); mix[:len(st)] += st[:N] * 0.75
    t0 = 0.0
    for kind, dur, layer, clip in segs:
        if clip:
            v = tts.read_wav(clip); i = int((t0 + 0.35) * SR)
            mix[i:i + len(v)] += v[: max(0, N - i)] * 0.95
        t0 += dur
    mix = mix / max(1.0, np.abs(mix).max() / 0.97)
    wav = os.path.join(tmp, "mix.wav")
    with wave.open(wav, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())

    # ---- frames piped to ffmpeg ----
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a", "-shortest",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out_mp4]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    starts, acc = [], 0.0
    for s in segs:
        starts.append(acc); acc += s[1]
    frames = int(total * FPS)
    prev_bg = None
    for f in range(frames):
        ts = f / FPS
        k = max(i for i, s0 in enumerate(starts) if s0 <= ts)
        kind, dur, layer, _ = segs[k]
        local = ts - starts[k]
        if kind == "cover":
            frame = _zoom(story_big, 1.0 + 0.04 * local / dur, W, H)
        else:
            z = 1.0 + 0.06 * local / dur
            bg = _zoom(bgs[k - 1], z, W, BG_H)
            if k >= 2 and local < XFADE:
                pb = _zoom(bgs[k - 2], 1.06, W, BG_H)
                bg = Image.blend(pb, bg, local / XFADE)
            frame = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            frame.paste(bg, (0, 0))
            frame.alpha_composite(static)
            a = min(1.0, local / FADE, (dur - local) / FADE) if kind != "outro" else min(1.0, local / FADE)
            if a > 0.01:
                rise = int(30 * (1 - min(1.0, local / FADE)))
                lay = layer
                if a < 1:
                    lay = layer.copy(); lay.putalpha(layer.split()[3].point(lambda v, a=a: int(v * a)))
                frame.alpha_composite(lay, (0, rise))
            if k == 1 and local < XFADE:   # cross-fade out of the cover card
                frame = Image.blend(_zoom(story_big, 1.04, W, H).convert("RGBA"), frame, local / XFADE)
            frame = frame.convert("RGB")
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg failed while encoding the narrated Reel")
    for fn in os.listdir(tmp):
        os.remove(os.path.join(tmp, fn))
    os.rmdir(tmp)
    return {"duration": round(total, 2), "segments": len(segs), "narration_engine": engine,
            "scenes": scene_list, "seed": seed}


if __name__ == "__main__":
    req = json.load(open(sys.argv[1]))
    print(build(req, sys.argv[2], sys.argv[3]))
