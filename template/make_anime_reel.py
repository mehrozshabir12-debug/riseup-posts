"""Hand-painted anime-style landscape Reel (1080x1920, ~9 s) with the news headline.
No AI service needed: the scene is painted procedurally (big summer clouds, hills, grass,
houses, particles) and animated with parallax, so every video looks different.

Text style matches the post template (yellow bar + big white + yellow highlight), no boxes.
The story plays paragraph by paragraph; natural ambience + soft piano is synthesized (ambience.py).

Usage: python3 make_anime_reel.py cfg.json out.mp4
cfg: {"mood": "day|sunset|rain|night|spring" (optional, random),
      "line1": "yellow bar words", "line2": "big white headline", "sub": "white sub", "sub_hl": "yellow tail",
      "paragraphs": ["short paragraph, **highlight** key numbers", ...]   (3-6, ~15-30 words each),
      "question": "Aap ka kya khayal hai?", "source": "Dawn", "seed": 123 (optional)}
Total length = 5 s intro + paragraphs (by word count) + 5 s outro, max 60 s.
"""
import json, math, random, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

W, H = 1080, 1920
FPS = 24
PAD = 420                      # extra width for the camera pan
BW = W + PAD
YELLOW = (255, 221, 0)
BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
HERE = os.path.dirname(os.path.abspath(__file__))

MOODS = {
    #        sky top,        sky bottom,      cloud light,     cloud shadow,    far hills,      near hills,      grass
    "day":    ((40, 120, 215), (165, 215, 245), (255, 255, 252), (150, 175, 215), (105, 150, 190), (70, 150, 70), (45, 120, 45)),
    "spring": ((70, 150, 225), (200, 230, 245), (255, 252, 250), (175, 180, 220), (130, 160, 200), (110, 170, 80), (70, 140, 55)),
    "sunset": ((60, 70, 150), (255, 170, 110), (255, 225, 190), (190, 120, 150), (120, 90, 140), (70, 80, 60), (45, 60, 40)),
    "rain":   ((70, 85, 105), (150, 165, 175), (205, 210, 215), (110, 120, 135), (95, 110, 120), (60, 100, 70), (40, 80, 50)),
    "night":  ((8, 15, 45), (40, 60, 110), (120, 135, 175), (55, 65, 105), (35, 50, 85), (25, 50, 45), (15, 35, 30)),
}


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgrad(w, h, top, bot):
    g = Image.new("RGB", (1, h))
    for y in range(h):
        g.putpixel((0, y), lerp(top, bot, y / (h - 1)))
    return g.resize((w, h))


def cloud(rng, w, h, light, shadow):
    """towering anime cumulus: many crisp puffs, white lit tops, lavender shaded underside."""
    pad = 60
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    base = int(h * 0.80)
    puffs = []
    # bottom row
    x = pad + 40
    while x < w - pad - 40:
        r = rng.randint(int(h * 0.10), int(h * 0.16))
        puffs.append((x, base - r * 0.6, r)); x += int(r * 1.1)
    # stacked rows getting narrower toward the top
    for row in range(1, 4):
        cx0, half = w / 2 + rng.randint(-40, 40), (w / 2 - pad) * (1 - row * 0.22)
        for _ in range(rng.randint(4, 7) - row):
            r = rng.randint(int(h * 0.12), int(h * 0.19))
            cx = rng.uniform(cx0 - half + r, cx0 + half - r)
            cy = base - r * 0.6 - row * h * 0.17 - rng.randint(0, 20)
            puffs.append((cx, max(r + 10, cy), r))
    for cx, cy, r in puffs:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    d.rectangle((0, base, w, h), fill=0)
    m = m.filter(ImageFilter.GaussianBlur(1.2))
    # per-puff shading: lit upper-left, shadow lower-right
    body = Image.new("RGB", (w, h), shadow)
    lit = Image.new("L", (w, h), 0)
    ld = ImageDraw.Draw(lit)
    for cx, cy, r in puffs:
        ld.ellipse((cx - r * 0.95, cy - r * 0.98, cx + r * 0.7, cy + r * 0.45), fill=255)
    lit = lit.filter(ImageFilter.GaussianBlur(6))
    vert = Image.linear_gradient("L").resize((w, h)).point(lambda v: 255 - v)   # brighter at top
    lit = ImageChops.multiply(lit, vert.point(lambda v: min(255, v + 90)))
    body = Image.composite(Image.new("RGB", (w, h), light), body, lit)
    # flat soft bottom band
    band = Image.new("L", (w, h), 0)
    ImageDraw.Draw(band).rectangle((0, base - int(h * 0.10), w, h), fill=170)
    body = Image.composite(Image.new("RGB", (w, h), lerp(shadow, (90, 90, 140), 0.25)), body, band.filter(ImageFilter.GaussianBlur(14)))
    out = body.convert("RGBA")
    out.putalpha(m)
    return out


def brush(img, rng, region_pts, cols, n=900, rx=(10, 26), ry=(4, 10)):
    """painterly dabs over a hill layer (only where the layer is opaque)."""
    tex = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(tex)
    w, h = img.size
    ys = {int(x): y for x, y in region_pts}
    for _ in range(n):
        x = rng.randint(0, w - 1)
        top = ys.get(x - x % 8, h)
        y = rng.randint(int(top), min(h - 1, int(top) + 420))
        a, b = rng.randint(*rx), rng.randint(*ry)
        d.ellipse((x - a, y - b, x + a, y + b), fill=rng.choice(cols) + (rng.randint(70, 150),))
    tex.putalpha(ImageChops.multiply(tex.split()[3], img.split()[3]))
    return Image.alpha_composite(img, tex)


def hills(rng, w, top_y, amp, col, col2, h=H):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ph = [rng.random() * 6 for _ in range(3)]
    pts = []
    for x in range(0, w + 8, 8):
        y = top_y + amp * (0.6 * math.sin(x / 260 + ph[0]) + 0.3 * math.sin(x / 110 + ph[1]) + 0.1 * math.sin(x / 47 + ph[2]))
        pts.append((x, y))
    d.polygon(pts + [(w, h), (0, h)], fill=col + (255,))
    # soft gradient shading downward
    shade = vgrad(w, h, col, col2).convert("RGBA")
    mask = img.split()[3]
    img = Image.composite(shade, img, mask)
    img.putalpha(mask)
    return img, pts


def house(d, x, y, s, rng):
    wall = rng.choice([(245, 235, 215), (235, 225, 200), (250, 240, 230)])
    roof = rng.choice([(190, 70, 55), (70, 110, 160), (160, 90, 60), (90, 120, 80)])
    d.rectangle((x, y - 60 * s, x + 90 * s, y), fill=wall, outline=(90, 70, 60), width=2)
    d.polygon([(x - 12 * s, y - 58 * s), (x + 45 * s, y - 105 * s), (x + 102 * s, y - 58 * s)], fill=roof, outline=(70, 50, 40))
    d.rectangle((x + 15 * s, y - 42 * s, x + 35 * s, y - 22 * s), fill=(255, 220, 140))
    d.rectangle((x + 55 * s, y - 40 * s, x + 75 * s, y), fill=(120, 80, 60))


def tree(d, x, y, s, col, rng):
    d.rectangle((x - 6 * s, y - 70 * s, x + 6 * s, y), fill=(95, 70, 50))
    for k in range(5):
        r = rng.randint(28, 40) * s
        cx = x + rng.randint(-30, 30) * s; cy = y - 90 * s - rng.randint(0, 50) * s
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=lerp(col, (255, 255, 200), rng.uniform(0, 0.25)))


def paper(rng):
    n = Image.effect_noise((W // 2, H // 2), 22).resize((W, H)).filter(ImageFilter.GaussianBlur(1))
    return n


REG = "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf"
MX = 52
FADE_START, FADE_END = 830, 1150   # scene fades into black here, exactly like the post image
TEXT_TOP = 1180


def F(sz, bold=True):
    return ImageFont.truetype(BOLD if bold else REG, sz)


def tw_(d, t, f, sw):
    b = d.textbbox((0, 0), t, font=f, stroke_width=sw); return b[2] - b[0]


def fit(d, t, max_w, start, minimum):
    s_ = start
    while s_ > minimum:
        f = F(s_)
        if tw_(d, t, f, int(s_ * 0.016)) <= max_w:
            return f, int(s_ * 0.016)
        s_ -= 2
    return F(minimum), int(minimum * 0.016)


def dt(d, xy, t, f, sw, fill):
    d.text(xy, t, font=f, fill=fill, stroke_width=sw, stroke_fill=fill)


def static_layer():
    """black fade, logo corner, logo + wordmark, social icons: same as make_post.py."""
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = Image.new("L", (1, H), 0)
    for y in range(FADE_START, H):
        v = 255 if y >= FADE_END else int(255 * ((y - FADE_START) / (FADE_END - FADE_START)) ** 1.4)
        g.putpixel((0, y), v)
    L.putalpha(g.resize((W, H)))
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).ellipse((-220, -200, 520, 300), fill=120)
    sh = sh.filter(ImageFilter.GaussianBlur(70))
    L.putalpha(ImageChops.lighter(L.split()[3], sh))
    d = ImageDraw.Draw(L)
    logo = Image.open(os.path.join(HERE, "assets", "logo_white.png"))
    lh = 112
    logo = logo.resize((round(logo.width * lh / logo.height), lh), Image.LANCZOS)
    L.alpha_composite(logo, (MX, 40))
    wf = F(38)
    d.text((MX + logo.width + 14, 52), "RISEUP", font=wf, fill=(255, 255, 255, 255))
    d.text((MX + logo.width + 14, 94), "PAKISTAN", font=wf, fill=(255, 255, 255, 255))
    icons = [Image.open(os.path.join(HERE, "assets", f"icon_{n}.png")).convert("RGBA") for n in ("facebook", "instagram", "tiktok")]
    ih = 46
    icons = [i.resize((round(i.width * ih / i.height), ih), Image.LANCZOS) for i in icons]
    gap = 34
    total = sum(i.width for i in icons) + gap * 2 * (len(icons) - 1)
    x = (W - total) // 2; iy = H - 96
    for k, ic in enumerate(icons):
        L.alpha_composite(ic, (x, iy)); x += ic.width
        if k < len(icons) - 1:
            x += gap; d.line([(x, iy - 4), (x, iy + ih + 4)], fill=(230, 230, 230, 255), width=2); x += gap
    return L


def yellow_line1(d, text, y):
    max_w = W - 2 * MX - 30
    f1, sw1 = fit(d, text, max_w, 98, 60)
    b = d.textbbox((0, 0), text, font=f1, stroke_width=sw1)
    tw, th = b[2] - b[0], b[3] - b[1]
    d.rectangle((MX, y, MX + tw + 36, y + th + 28), fill=YELLOW)
    dt(d, (MX + 18 - b[0], y + 14 - b[1]), text, f1, sw1, (0, 0, 0))
    return y + th + 28 + 20


def big_white(d, text, y):
    f2, sw2 = fit(d, text, W - 2 * MX, 116, 64)
    b = d.textbbox((0, 0), text, font=f2, stroke_width=sw2)
    dt(d, (MX - b[0], y - b[1]), text, f2, sw2, (255, 255, 255))
    return y + (b[3] - b[1]) + 30


def sub_text(d, text, y, size=56, max_lines=None):
    """white bold text; **words** get the yellow box like sub_hl in the post."""
    fs = F(size); sws = 1
    max_w = W - 2 * MX - 30
    toks, hl = [], False
    for w_ in text.split():
        if w_.startswith("**"):
            hl = True
        clean = w_.strip("*")
        toks.append((clean, hl))
        if w_.endswith("**") and (len(w_) > 2 or hl):
            hl = False
    # group into runs (normal text / highlighted), then wrap word by word
    asc = d.textbbox((0, 0), "Hg", font=fs, stroke_width=sws)
    lh = asc[3] - asc[1]; gap = 14
    sp = tw_(d, " ", fs, sws) + 4
    x = MX
    lines = [[]]
    for wd, h in toks:
        w = tw_(d, wd, fs, sws) + (30 if h else 0)
        if x > MX and x + w > MX + max_w:
            lines.append([]); x = MX
        lines[-1].append((wd, h, x)); x += w + (sp if not h else 12)
    for ln in lines:
        # merge neighbouring highlighted words into one box
        i = 0
        while i < len(ln):
            wd, h, x0 = ln[i]
            if h:
                words = [wd]; j = i + 1
                while j < len(ln) and ln[j][1]:
                    words.append(ln[j][0]); j += 1
                txt = " ".join(words)
                w = tw_(d, txt, fs, sws) + 30
                d.rectangle((x0, y - 8, x0 + w, y + lh + 10), fill=YELLOW)
                dt(d, (x0 + 15, y - asc[1]), txt, fs, sws, (0, 0, 0))
                # shift the rest of the line to follow the merged box
                shift = (x0 + w + 12) - (ln[j][2] if j < len(ln) else x0 + w + 12)
                ln[j:] = [(a, b_, c + shift) for a, b_, c in ln[j:]]
                i = j
            else:
                dt(d, (x0, y - asc[1]), wd, fs, sws, (255, 255, 255)); i += 1
        y += lh + gap
    return y


def rule_tag(d, y, tag):
    y += 18
    d.rectangle((MX, y, MX + 140, y + 6), fill=YELLOW)
    y += 26
    d.text((MX, y), tag or "", font=F(36, False), fill=(255, 255, 255))


def intro_layer(cfg):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    y = yellow_line1(d, cfg["line1"], TEXT_TOP)
    y = big_white(d, cfg["line2"], y)
    sub = cfg.get("sub", "") + (" **" + cfg["sub_hl"] + "**" if cfg.get("sub_hl") else "")
    y = sub_text(d, sub, y)
    rule_tag(d, y, cfg.get("tag", ""))
    return L


def para_layer(cfg, text, i, n):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    y = yellow_line1(d, cfg["line1"], TEXT_TOP) + 10
    size = 56
    while size > 44:  # shrink if the paragraph would run into the icons
        test = Image.new("RGBA", (W, H)); td = ImageDraw.Draw(test)
        if sub_text(td, text, y, size) < H - 260:
            break
        size -= 4
    y = sub_text(d, text, y, size)
    rule_tag(d, y, f"{cfg.get('tag', '')}  ·  {i + 1}/{n}" if cfg.get("tag") else f"{i + 1}/{n}")
    return L


def outro_layer(cfg):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    y = yellow_line1(d, "Aap ki raye?", TEXT_TOP)
    q = cfg.get("question", "Aap ka kya khayal hai?")
    y = sub_text(d, q, y, 72)
    y = sub_text(d, "Comment mein batayein aur **Follow karein**", y + 6)
    rule_tag(d, y, ("Source: " + cfg["source"]) if cfg.get("source") else "")
    return L


def build_segments(cfg):
    segs = [("intro", 5.0, intro_layer(cfg))]
    paras = cfg.get("paragraphs", [])
    for i, p in enumerate(paras):
        words = len(p.replace("**", "").split())
        segs.append(("para", max(5.0, min(11.0, words / 2.6 + 1.8)), para_layer(cfg, p, i, len(paras))))
    segs.append(("outro", 5.0, outro_layer(cfg)))
    total = sum(s[1] for s in segs)
    if total > 60:  # shrink paragraph time proportionally
        k = (60 - 10) / (total - 10)
        segs = [(a, b * k if a == "para" else b, c) for a, b, c in segs]
    return segs


def faded(layer, a, cache):
    key = (id(layer), round(a, 2))
    if key not in cache:
        l2 = layer.copy(); l2.putalpha(layer.split()[3].point(lambda v: int(v * a)))
        cache[key] = l2
    return cache[key]


def main():
    cfg = json.load(open(sys.argv[1])); out = sys.argv[2]
    seed = cfg.get("seed") or random.randrange(10**9)
    rng = random.Random(seed)
    mood = cfg.get("mood") or rng.choice(list(MOODS))
    sky_t, sky_b, c_l, c_s, far, near, grass = MOODS[mood]
    horizon = rng.randint(700, 800)

    sky = vgrad(BW, H, sky_t, sky_b).convert("RGBA")
    if mood == "night":
        sd = ImageDraw.Draw(sky)
        for _ in range(260):
            x, y, r = rng.randint(0, BW), rng.randint(0, horizon), rng.choice([1, 1, 2, 3])
            sd.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 230, rng.randint(120, 255)))
        mx, my = rng.randint(200, BW - 200), rng.randint(250, 500)
        moon = Image.new("RGBA", (BW, H), (0, 0, 0, 0))
        ImageDraw.Draw(moon).ellipse((mx - 80, my - 80, mx + 80, my + 80), fill=(255, 250, 220, 255))
        sky = Image.alpha_composite(sky, moon.filter(ImageFilter.GaussianBlur(25)))
        sky = Image.alpha_composite(sky, moon)
    elif mood == "sunset":
        sun = Image.new("RGBA", (BW, H), (0, 0, 0, 0))
        sx = rng.randint(250, BW - 250)
        ImageDraw.Draw(sun).ellipse((sx - 120, horizon - 260, sx + 120, horizon - 20), fill=(255, 220, 150, 255))
        sky = Image.alpha_composite(sky, sun.filter(ImageFilter.GaussianBlur(40)))
        sky = Image.alpha_composite(sky, sun)

    # clouds: (image, x, y, speed px/frame)
    clouds = []
    for i in range(rng.randint(2, 4)):
        cw = rng.randint(600, 1000); ch = int(cw * rng.uniform(0.7, 0.95))
        img = cloud(rng, cw, ch, c_l, c_s)
        clouds.append((img, rng.randint(-300, BW - 200), rng.randint(120, max(130, horizon - ch + 40)), rng.uniform(0.4, 1.4)))
    clouds.sort(key=lambda c: c[3])

    far_l, _ = hills(rng, BW, horizon - 80, 70, far, lerp(far, sky_b, 0.4))
    mid_l, mid_pts = hills(rng, BW, horizon + 40, 60, near, lerp(near, (20, 40, 20), 0.5))
    mid_l = brush(mid_l, rng, mid_pts, [lerp(near, (230, 240, 140), 0.35), lerp(near, (20, 50, 20), 0.3), near], n=1400)
    far_l = brush(far_l, rng, [(x, horizon - 150) for x in range(0, BW, 8)], [lerp(far, sky_b, 0.3), lerp(far, (40, 60, 90), 0.2)], n=500)
    md = ImageDraw.Draw(mid_l)
    for k in range(rng.randint(2, 5)):
        x = rng.randint(80, BW - 180)
        yy = min(p[1] for p in mid_pts if abs(p[0] - x) < 60) + 40
        if rng.random() < 0.5:
            house(md, x, yy + 10, rng.uniform(0.8, 1.2), rng)
        else:
            tree(md, x, yy + 10, rng.uniform(0.9, 1.4), lerp(near, (40, 90, 40), 0.3), rng)
    front_l, front_pts = hills(rng, BW + 200, horizon + 260, 50, grass, lerp(grass, (10, 25, 10), 0.6))
    front_l = brush(front_l, rng, front_pts, [lerp(grass, (220, 240, 120), 0.4), lerp(grass, (10, 40, 10), 0.4), grass],
                    n=2600, rx=(6, 16), ry=(10, 30))

    paper_rgb = Image.merge("RGB", [paper(rng).point(lambda v: 225 + v // 8)] * 3)
    particles = [[rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1, 3), rng.uniform(0, 6)] for _ in range(70)]
    kind = {"rain": "rain", "night": "firefly", "spring": "petal"}.get(mood, rng.choice(["leaf", "petal", "none"]))
    r2 = random.Random(seed + 1)
    ys = {int(px): py for px, py in front_pts}
    blades = [(r2.randint(0, W + PAD), r2.randint(10, 420), r2.randint(40, 120),
               lerp(grass, (200, 230, 120), r2.uniform(0, 0.5))) for _ in range(320)]

    segs = build_segments(cfg)
    total = sum(s[1] for s in segs)
    N = int(total * FPS)
    starts, acc = [], 0.0
    for s_ in segs:
        starts.append(acc); acc += s_[1]
    static = static_layer(); cache = {}
    FADE = 0.45

    tmp = out + "_frames"
    os.makedirs(tmp, exist_ok=True)
    for f in range(N):
        tsec = f / FPS
        t = f / max(1, N - 1)
        cam = int(PAD * t)
        frame = sky.crop((int(cam * 0.2), 0, int(cam * 0.2) + W, H)).copy()
        for img, x, y, sp in clouds:
            xx = (x + sp * f * 0.6 - cam * 0.3)
            xx = (xx + img.width) % (BW + img.width) - img.width   # wrap around for long videos
            frame.alpha_composite(img, (int(xx), int(y)))
        frame.alpha_composite(far_l.crop((int(cam * 0.4), 0, int(cam * 0.4) + W, H)))
        frame.alpha_composite(mid_l.crop((int(cam * 0.7), 0, int(cam * 0.7) + W, H)))
        frame.alpha_composite(front_l.crop((cam, 0, cam + W, H)))
        gd = ImageDraw.Draw(frame)
        for bx, off, hgt, col in blades:
            x = bx - cam
            if not -10 < x < W + 10:
                continue
            base = ys.get(bx - bx % 8, H) + off
            sway = 10 * math.sin(f / 8 + bx / 50)
            gd.line([(x, base), (x + sway, base - hgt)], fill=col + (255,), width=4)
        for p in particles:
            if kind == "rain":
                y = (p[1] + f * 38 * p[2] / 2) % H; x = (p[0] - f * 4) % W
                gd.line([(x, y), (x - 6, y + 40)], fill=(220, 230, 255, 150), width=2)
            elif kind == "firefly":
                x = p[0] + 20 * math.sin(f / 20 + p[3]); y = (p[1] * 0.4 + horizon * 0.6) + 15 * math.cos(f / 15 + p[3])
                a = int(150 + 100 * math.sin(f / 6 + p[3]))
                gd.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 250, 150, a))
            elif kind in ("petal", "leaf"):
                y = (p[1] + f * 3 * p[2]) % H; x = (p[0] + f * 2 + 30 * math.sin(f / 12 + p[3])) % W
                c = (255, 190, 210) if kind == "petal" else (150, 200, 90)
                gd.ellipse((x - 7, y - 4, x + 7, y + 4), fill=c + (220,))
        rgb = ImageChops.multiply(frame.convert("RGB"), paper_rgb).convert("RGBA")
        rgb.alpha_composite(static)
        # current text segment with fade + slight rise
        for (kind_s, dur, layer), st in zip(segs, starts):
            if st <= tsec < st + dur:
                local = tsec - st
                a = min(1.0, local / FADE, (dur - local) / FADE) if kind_s != "outro" else min(1.0, local / FADE)
                a = max(0.0, a)
                rise = int(30 * (1 - min(1.0, local / FADE)))
                if a > 0.01:
                    rgb.alpha_composite(faded(layer, a, cache) if a < 1 else layer, (0, rise))
        rgb.convert("RGB").save(f"{tmp}/{f:05d}.jpg", quality=88)

    import ambience
    wav = out + ".wav"
    ambience.make_audio(wav, N / FPS, mood, seed)
    cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", f"{tmp}/%05d.jpg", "-i", wav,
           "-map", "0:v", "-map", "1:a", "-shortest", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True, capture_output=True)
    for fn in os.listdir(tmp):
        os.remove(os.path.join(tmp, fn))
    os.rmdir(tmp); os.remove(wav)
    print(f"saved {out} mood={mood} seed={seed} length={N / FPS:.1f}s")


if __name__ == "__main__":
    main()
