"""Hand-painted anime-style landscape Reel (1080x1920, ~9 s) with the news headline.
No AI service needed: the scene is painted procedurally (big summer clouds, hills, grass,
houses, particles) and animated with parallax, so every video looks different.

Usage: python3 make_anime_reel.py cfg.json out.mp4
cfg: {"mood": "day|sunset|rain|night|spring", "line1": "...", "line2": "...", "sub": "...",
      "tag": "...", "seed": 123 (optional)}
"""
import json, math, random, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

W, H = 1080, 1920
FPS, DUR = 24, 9
PAD = 260                      # extra width for the camera pan
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


def wrap(d, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur); cur = w_
    if cur:
        lines.append(cur)
    return lines


def text_layer(cfg):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    # logo
    logo = Image.open(os.path.join(HERE, "assets", "logo_white.png"))
    lh = 100
    logo = logo.resize((round(logo.width * lh / logo.height), lh), Image.LANCZOS)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((40, 50, 60 + logo.width + 270, 170), radius=30, fill=(0, 0, 0, 110))
    L = Image.alpha_composite(L, sh)
    L.paste(logo, (60, 60), logo)
    d = ImageDraw.Draw(L)
    wf = ImageFont.truetype(BOLD, 36)
    d.text((70 + logo.width, 66), "RISEUP", font=wf, fill="white")
    d.text((70 + logo.width, 106), "PAKISTAN", font=wf, fill="white")
    # bottom card
    f1 = ImageFont.truetype(BOLD, 64); f2 = ImageFont.truetype(BOLD, 84); f3 = ImageFont.truetype(BOLD, 46)
    l2 = wrap(d, cfg["line2"], f2, W - 140)
    l3 = wrap(d, cfg.get("sub", ""), f3, W - 140)
    hgt = 110 + len(l2) * 100 + len(l3) * 60 + 120
    top = H - 140 - hgt
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle((40, top, W - 40, H - 120), radius=40, fill=(10, 20, 30, 185))
    L = Image.alpha_composite(L, card)
    d = ImageDraw.Draw(L)
    y = top + 40
    tw = d.textlength(cfg["line1"], font=f1)
    d.rounded_rectangle((70, y, 70 + tw + 40, y + 88), radius=16, fill=YELLOW)
    d.text((90, y + 8), cfg["line1"], font=f1, fill="black")
    y += 115
    for ln in l2:
        d.text((70, y), ln, font=f2, fill="white"); y += 100
    for ln in l3:
        d.text((70, y), ln, font=f3, fill=(235, 235, 235)); y += 60
    if cfg.get("tag"):
        d.text((70, y + 20), cfg["tag"], font=ImageFont.truetype(BOLD, 34), fill=YELLOW)
    return L


def main():
    cfg = json.load(open(sys.argv[1])); out = sys.argv[2]
    seed = cfg.get("seed") or random.randrange(10**9)
    rng = random.Random(seed)
    mood = cfg.get("mood") or rng.choice(list(MOODS))
    sky_t, sky_b, c_l, c_s, far, near, grass = MOODS[mood]
    horizon = rng.randint(1000, 1120)

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

    paper_tex = paper(rng)
    txt = text_layer(cfg)
    particles = [[rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1, 3), rng.uniform(0, 6)] for _ in range(70)]
    kind = {"rain": "rain", "night": "firefly", "spring": "petal"}.get(mood, rng.choice(["leaf", "petal", "none"]))

    tmp = out + "_frames"
    os.makedirs(tmp, exist_ok=True)
    N = FPS * DUR
    for f in range(N):
        t = f / (N - 1)
        cam = int(PAD * t)                     # camera pans left->right
        frame = sky.crop((int(cam * 0.2), 0, int(cam * 0.2) + W, H)).copy()
        for img, x, y, sp in clouds:
            frame.alpha_composite(img, (int(x + sp * f - cam * 0.3), int(y)))
        frame.alpha_composite(far_l.crop((int(cam * 0.4), 0, int(cam * 0.4) + W, H)))
        frame.alpha_composite(mid_l.crop((int(cam * 0.7), 0, int(cam * 0.7) + W, H)))
        fr = front_l.crop((cam, 0, cam + W, H))
        frame.alpha_composite(fr)
        # swaying grass blades
        gd = ImageDraw.Draw(frame)
        r2 = random.Random(seed + 1)
        for _ in range(320):
            x = r2.randint(0, W); base = H
            for px, py in front_pts:
                if abs(px - cam - x) < 8:
                    base = py; break
            base += r2.randint(10, 400)
            hgt = r2.randint(40, 120); sway = 10 * math.sin(f / 8 + x / 50)
            gd.line([(x, base), (x + sway, base - hgt)], fill=lerp(grass, (200, 230, 120), r2.uniform(0, 0.5)) + (255,), width=4)
        # particles
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
                col = (255, 190, 210) if kind == "petal" else (150, 200, 90)
                gd.ellipse((x - 7, y - 4, x + 7, y + 4), fill=col + (220,))
        rgb = frame.convert("RGB")
        rgb = ImageChops.multiply(rgb, Image.merge("RGB", [paper_tex.point(lambda v: 225 + v // 8)] * 3))
        rgb = rgb.convert("RGBA")
        # text fades in during the first second
        a = min(1.0, f / FPS)
        if a < 1:
            tl = txt.copy(); tl.putalpha(txt.split()[3].point(lambda v: int(v * a)))
        else:
            tl = txt
        rgb.alpha_composite(tl)
        rgb.convert("RGB").save(f"{tmp}/{f:04d}.jpg", quality=90)

    music = cfg.get("music")
    cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", f"{tmp}/%04d.jpg"]
    cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    cmd += ["-map", "0:v", "-map", "1:a", "-t", str(DUR), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True, capture_output=True)
    for fn in os.listdir(tmp):
        os.remove(os.path.join(tmp, fn))
    os.rmdir(tmp)
    print(f"saved {out} mood={mood} seed={seed}")


if __name__ == "__main__":
    main()
