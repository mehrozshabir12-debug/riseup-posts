"""Varied topic scenes for the top area of RiseUp Pakistan posts (1080x840).

Every scene is drawn with a random seed: background colours, element positions, sizes
and decorations change each time, so two posts on the same topic never look identical.
make_post.py picks a scene that was not used in the recent posts (see pick_scene).
"""
import math, random, json, os
from PIL import Image, ImageDraw, ImageFilter, ImageChops

W, H = 1080, 840
YELLOW = (255, 221, 0)

# background palettes: (inner glow, outer dark)
PALETTES = {
    "green":  ((10, 85, 55), (2, 14, 10)),
    "teal":   ((0, 85, 95), (2, 12, 16)),
    "navy":   ((25, 50, 120), (3, 6, 20)),
    "purple": ((70, 25, 120), (8, 3, 18)),
    "maroon": ((110, 20, 35), (14, 2, 5)),
    "amber":  ((110, 70, 10), (14, 9, 2)),
    "slate":  ((55, 65, 80), (6, 8, 12)),
    "orange": ((130, 50, 10), (16, 6, 2)),
    "sky":    ((20, 90, 150), (2, 10, 22)),
    "olive":  ((60, 80, 20), (8, 10, 2)),
}


# ---------------------------------------------------------------- helpers
def _bg(rng, palettes):
    name = rng.choice(palettes)
    c_in, c_out = PALETTES[name]
    cx, cy = rng.randint(250, 830), rng.randint(180, 520)
    r = rng.randint(480, 650)
    img = Image.new("RGB", (W, H), c_out)
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(r // 2))
    img = Image.composite(Image.new("RGB", (W, H), c_in), img, m)
    deco = rng.choice(["grid", "dots", "diag", "rings", "none"])
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    if deco == "grid":
        s = rng.choice([48, 60, 72])
        for x in range(0, W, s):
            d.line([(x, 0), (x, H)], fill=(255, 255, 255, 16))
        for y in range(0, H, s):
            d.line([(0, y), (W, y)], fill=(255, 255, 255, 16))
    elif deco == "dots":
        s = rng.choice([36, 44])
        for x in range(0, W, s):
            for y in range(0, H, s):
                d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 255, 255, 26))
    elif deco == "diag":
        for k in range(-H, W, 40):
            d.line([(k, 0), (k + H, H)], fill=(255, 255, 255, 12), width=2)
    elif deco == "rings":
        rx, ry = rng.randint(0, W), rng.randint(0, H)
        for i in range(10):
            rr = 80 + i * 70
            d.ellipse((rx - rr, ry - rr, rx + rr, ry + rr), outline=(255, 255, 255, 18), width=3)
    return Image.alpha_composite(img.convert("RGBA"), ov), name


def _glow(base, layer, blur=22, strength=2):
    """layer: RGBA drawing; adds a glow under it and pastes it on base."""
    rgb = Image.new("RGB", (W, H), (0, 0, 0))
    rgb.paste(layer, (0, 0), layer)
    g = rgb.filter(ImageFilter.GaussianBlur(blur))
    out = base.convert("RGB")
    for _ in range(strength):
        out = ImageChops.screen(out, g)
    out = out.convert("RGBA")
    return Image.alpha_composite(out, layer)


def _new():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def _star(cx, cy, r, ri, n=5, rot=0):
    pts = []
    for i in range(n * 2):
        a = -math.pi / 2 + rot + i * math.pi / n
        rr = r if i % 2 == 0 else ri
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def _side(rng):
    """main object x-centre: left, centre or right third."""
    return rng.choice([360, 540, 720])


def _sparkles(d, rng, n, col=(255, 255, 255)):
    for _ in range(n):
        x, y, r = rng.randint(20, W - 20), rng.randint(20, 640), rng.randint(3, 9)
        d.polygon(_star(x, y, r * 2, r * 0.5, 4), fill=col + (rng.randint(90, 200),))


# ---------------------------------------------------------------- scenes
def gold(rng):
    img, _ = _bg(rng, ["amber", "maroon", "navy", "slate", "purple"])
    L = _new(); d = ImageDraw.Draw(L)
    cx = _side(rng); base = rng.randint(560, 640)
    bw, bh = rng.randint(170, 200), 80
    rows = rng.choice([[3, 2, 1], [2, 1], [3, 2]])
    for ri, n in enumerate(rows):
        y = base - ri * (bh - 8)
        x0 = cx - n * bw // 2
        for i in range(n):
            x = x0 + i * bw
            d.polygon([(x + 18, y - bh), (x + bw - 18, y - bh), (x + bw - 4, y), (x + 4, y)],
                      fill=(240, 180, 30, 255), outline=(255, 235, 140, 255))
            d.polygon([(x + 30, y - bh + 8), (x + bw - 30, y - bh + 8), (x + bw - 36, y - bh + 26), (x + 36, y - bh + 26)],
                      fill=(255, 225, 110, 255))
    _sparkles(d, rng, rng.randint(10, 22), (255, 240, 170))
    return _glow(img, L, blur=28, strength=2)


def fuel(rng):
    img, _ = _bg(rng, ["maroon", "orange", "navy", "slate", "teal"])
    L = _new(); d = ImageDraw.Draw(L)
    cx = _side(rng); col = rng.choice([(230, 40, 40), (0, 170, 90), (30, 120, 230), (240, 150, 0)])
    x0, y0 = cx - 140, 170
    d.rounded_rectangle((x0, y0, x0 + 280, y0 + 520), radius=26, fill=col + (255,))
    d.rounded_rectangle((x0 + 35, y0 + 45, x0 + 245, y0 + 200), radius=14, fill=(20, 25, 35, 255))
    for k in range(3):
        d.rectangle((x0 + 55, y0 + 65 + k * 42, x0 + 225, y0 + 92 + k * 42), fill=(80, 255, 160, 200))
    d.rounded_rectangle((x0 + 60, y0 + 250, x0 + 220, y0 + 330), radius=10, fill=(255, 255, 255, 230))
    # hose + nozzle
    d.arc((x0 + 200, y0 + 200, x0 + 420, y0 + 520), 270, 90, fill=(30, 30, 30, 255), width=16)
    d.rounded_rectangle((x0 + 300, y0 + 480, x0 + 380, y0 + 520), radius=8, fill=(40, 40, 40, 255))
    # drop
    dx, dy = cx + rng.choice([-260, 260]), rng.randint(250, 420)
    if not 80 < dx < W - 80:
        dx = W - dx
    d.ellipse((dx - 60, dy, dx + 60, dy + 120), fill=(255, 200, 40, 255))
    d.polygon([(dx, dy - 90), (dx - 57, dy + 45), (dx + 57, dy + 45)], fill=(255, 200, 40, 255))
    return _glow(img, L, blur=24)


def electricity(rng):
    img, _ = _bg(rng, ["navy", "purple", "slate", "teal", "amber"])
    L = _new(); d = ImageDraw.Draw(L)
    cx = _side(rng); cy = rng.randint(280, 340)
    glow = rng.choice([(255, 221, 0), (255, 170, 40), (120, 220, 255)])
    d.ellipse((cx - 150, cy - 160, cx + 150, cy + 140), fill=glow + (255,))
    d.polygon([(cx - 85, cy + 100), (cx + 85, cy + 100), (cx + 60, cy + 190), (cx - 60, cy + 190)], fill=glow + (255,))
    for k in range(4):
        d.rounded_rectangle((cx - 70, cy + 195 + k * 28, cx + 70, cy + 215 + k * 28), radius=8, fill=(170, 175, 185, 255))
    # filament bolt
    d.line([(cx - 40, cy - 40), (cx, cy + 20), (cx - 10, cy + 20), (cx + 40, cy + 90)], fill=(255, 255, 255, 255), width=8)
    # pylons / cables
    px = 140 if cx > 540 else 940
    for dx in (-60, 60):
        d.line([(px + dx, 760), (px, 140)], fill=(200, 210, 230, 200), width=6)
    for y in (240, 340, 440):
        d.line([(px - 90, y), (px + 90, y)], fill=(200, 210, 230, 200), width=5)
    d.line([(0, 250), (px - 90, 240), (W, 300)], fill=(200, 210, 230, 120), width=3)
    return _glow(img, L, blur=34, strength=2)


def currency(rng):
    img, _ = _bg(rng, ["green", "teal", "olive", "slate", "navy"])
    L = _new(); d = ImageDraw.Draw(L)
    cx, cy = _side(rng), rng.randint(330, 430)
    for k in range(rng.randint(4, 6)):
        ang = rng.uniform(-25, 25)
        note = Image.new("RGBA", (420, 200), (0, 0, 0, 0))
        nd = ImageDraw.Draw(note)
        col = rng.choice([(40, 150, 90), (60, 170, 110), (90, 160, 70), (150, 120, 60)])
        nd.rounded_rectangle((0, 0, 419, 199), radius=14, fill=col + (255,), outline=(220, 255, 220, 255), width=4)
        nd.ellipse((150, 40, 270, 160), outline=(230, 255, 230, 255), width=6)
        nd.text((190, 70), rng.choice(["$", "Rs"]), fill=(230, 255, 230, 255))
        note = note.rotate(ang, expand=True, resample=Image.BICUBIC)
        L.paste(note, (cx - note.width // 2 + rng.randint(-120, 120), cy - note.height // 2 + rng.randint(-120, 100)), note)
    # up/down arrow
    up = rng.random() < 0.5
    ax = 160 if cx > 540 else 920
    col = (0, 230, 120, 255) if up else (255, 70, 70, 255)
    if up:
        d.polygon([(ax, 160), (ax - 80, 280), (ax - 30, 280), (ax - 30, 520), (ax + 30, 520), (ax + 30, 280), (ax + 80, 280)], fill=col)
    else:
        d.polygon([(ax, 560), (ax - 80, 440), (ax - 30, 440), (ax - 30, 200), (ax + 30, 200), (ax + 30, 440), (ax + 80, 440)], fill=col)
    return _glow(img, L, blur=22)


def tax(rng):
    img, _ = _bg(rng, ["slate", "navy", "teal", "purple", "maroon"])
    L = _new(); d = ImageDraw.Draw(L)
    cx = _side(rng); y0 = rng.randint(120, 170)
    # document
    d.rounded_rectangle((cx - 170, y0, cx + 170, y0 + 470), radius=18, fill=(240, 244, 250, 255))
    d.rectangle((cx - 130, y0 + 40, cx + 40, y0 + 70), fill=(40, 60, 90, 255))
    for k in range(7):
        w = rng.randint(140, 260)
        d.rectangle((cx - 130, y0 + 110 + k * 42, cx - 130 + w, y0 + 124 + k * 42), fill=(150, 165, 185, 255))
    # stamp
    sc = rng.choice([(220, 40, 40), (0, 150, 90), (30, 90, 200)])
    d.ellipse((cx + 40, y0 + 300, cx + 160, y0 + 420), outline=sc + (255,), width=10)
    d.ellipse((cx + 70, y0 + 330, cx + 130, y0 + 390), fill=sc + (200,))
    # calculator
    kx = cx + (220 if cx < 700 else -420); ky = y0 + 200
    d.rounded_rectangle((kx, ky, kx + 200, ky + 290), radius=18, fill=(35, 40, 55, 255), outline=(160, 180, 210, 255), width=4)
    d.rectangle((kx + 20, ky + 20, kx + 180, ky + 75), fill=(140, 230, 170, 255))
    for r in range(4):
        for c in range(3):
            d.rounded_rectangle((kx + 22 + c * 55, ky + 95 + r * 47, kx + 67 + c * 55, ky + 132 + r * 47), radius=6,
                                fill=(255, 221, 0, 255) if (r, c) == (3, 2) else (90, 100, 125, 255))
    return _glow(img, L, blur=26, strength=1)


def people(rng):
    """crowd silhouettes – poverty, jobs, population, social stories"""
    img, _ = _bg(rng, ["orange", "maroon", "slate", "amber", "purple"])
    L = _new(); d = ImageDraw.Draw(L)
    sun_x = rng.randint(200, 880)
    d.ellipse((sun_x - 170, 180, sun_x + 170, 520), fill=rng.choice([(255, 170, 60, 255), (255, 210, 90, 255), (255, 120, 80, 255)]))
    img = _glow(img, L, blur=50, strength=2)
    S = _new(); s = ImageDraw.Draw(S)
    x = -30
    while x < W + 30:
        h = rng.randint(220, 330); w = int(h * 0.36); top = 840 - h
        s.ellipse((x - w * 0.32, top, x + w * 0.32, top + w * 0.64), fill=(8, 8, 12, 255))
        s.rounded_rectangle((x - w // 2, top + w * 0.7, x + w // 2, 860), radius=w // 3, fill=(8, 8, 12, 255))
        x += rng.randint(70, 120)
    return Image.alpha_composite(img, S)


def heat(rng):
    img, _ = _bg(rng, ["orange", "maroon", "amber"])
    L = _new(); d = ImageDraw.Draw(L)
    sx, sy = rng.randint(250, 830), rng.randint(200, 300)
    d.ellipse((sx - 130, sy - 130, sx + 130, sy + 130), fill=(255, 190, 40, 255))
    for k in range(16):
        a = k * math.pi / 8 + rng.uniform(0, 0.2)
        d.line([(sx + 160 * math.cos(a), sy + 160 * math.sin(a)), (sx + 215 * math.cos(a), sy + 215 * math.sin(a))],
               fill=(255, 190, 40, 255), width=12)
    tx = 170 if sx > 540 else 900
    d.rounded_rectangle((tx - 30, 160, tx + 30, 560), radius=30, outline=(255, 255, 255, 255), width=8)
    d.ellipse((tx - 60, 530, tx + 60, 650), fill=(240, 40, 40, 255))
    d.rectangle((tx - 14, 260, tx + 14, 580), fill=(240, 40, 40, 255))
    for y in (600, 660, 720):  # heat waves
        pts = [(x, y + 14 * math.sin(x / 45)) for x in range(0, W, 12)]
        d.line(pts, fill=(255, 220, 160, 110), width=5)
    return _glow(img, L, blur=30, strength=2)


def wind(rng):
    img, _ = _bg(rng, ["sky", "teal", "slate", "navy"])
    L = _new(); d = ImageDraw.Draw(L)
    for _ in range(rng.randint(6, 9)):
        y = rng.randint(120, 640); x0 = rng.randint(-50, 300); ln = rng.randint(380, 720)
        amp = rng.randint(10, 30)
        pts = [(x, y + amp * math.sin((x - x0) / 70)) for x in range(x0, x0 + ln, 10)]
        d.line(pts, fill=(220, 240, 255, rng.randint(140, 230)), width=rng.randint(6, 12))
        ex, ey = pts[-1]
        d.arc((ex - 40, ey - 70, ex + 40, ey + 10), 90, 330, fill=(220, 240, 255, 200), width=8)
    # palm tree bending
    px = rng.choice([150, 820])
    d.line([(px, 840), (px + 20, 600), (px + 70, 420)], fill=(30, 25, 20, 255), width=26, joint="curve")
    for k in range(6):
        a = math.radians(-10 + k * 22)
        d.line([(px + 70, 420), (px + 70 + 230 * math.cos(a), 420 + 140 * math.sin(a) + 30)], fill=(15, 60, 35, 255), width=22)
    return _glow(img, L, blur=14, strength=1)


def rain(rng):
    img, _ = _bg(rng, ["navy", "slate", "sky", "teal"])
    L = _new(); d = ImageDraw.Draw(L)
    for _ in range(rng.randint(100, 170)):
        x, y = rng.randint(0, W), rng.randint(280, H)
        d.line([(x, y), (x - 12, y + 42)], fill=(170, 200, 255, 130), width=3)
    C = _new(); c = ImageDraw.Draw(C)
    for _ in range(rng.randint(4, 6)):
        x, y = rng.randint(100, 980), rng.randint(120, 330)
        rx, ry = rng.randint(200, 330), rng.randint(90, 150)
        g = rng.randint(95, 160)
        c.ellipse((x - rx, y - ry, x + rx, y + ry), fill=(g, g + 12, g + 35, 235))
    C = C.filter(ImageFilter.GaussianBlur(10))
    img = Image.alpha_composite(Image.alpha_composite(img, L), C)
    U = _new(); u = ImageDraw.Draw(U)
    if rng.random() < 0.6:  # umbrella
        ux, uy = rng.choice([260, 540, 820]), 520
        u.pieslice((ux - 170, uy - 150, ux + 170, uy + 150), 180, 360, fill=rng.choice([(230, 50, 60, 255), (255, 200, 0, 255), (40, 160, 230, 255)]))
        u.line([(ux, uy), (ux, uy + 200)], fill=(230, 230, 230, 255), width=10)
        u.arc((ux - 50, uy + 160, ux, uy + 230), 0, 180, fill=(230, 230, 230, 255), width=10)
    else:
        bx = rng.randint(350, 730)
        u.polygon([(bx, 330), (bx - 90, 520), (bx - 20, 520), (bx - 80, 720), (bx + 90, 470), (bx + 10, 470), (bx + 80, 330)], fill=YELLOW + (255,))
    return _glow(img, U, blur=26, strength=2)


def cricket(rng):
    img, _ = _bg(rng, ["green", "navy", "teal", "purple"])
    L = _new(); d = ImageDraw.Draw(L)
    for x in (rng.randint(80, 220), rng.randint(860, 1000)):  # floodlights
        for k in range(3):
            for j in range(4):
                d.ellipse((x - 70 + j * 36, 70 + k * 34, x - 50 + j * 36, 90 + k * 34), fill=(255, 250, 220, 255))
    img = _glow(img, L, blur=28, strength=3)
    O = _new(); o = ImageDraw.Draw(O)
    o.polygon([(0, 840), (260, 470), (820, 470), (1080, 840)], fill=(30, 120, 50, 255))
    o.polygon([(480, 840), (505, 480), (575, 480), (600, 840)], fill=(200, 175, 120, 255))
    variant = rng.choice(["ball", "bat", "stumps"])
    if variant in ("ball", "bat"):
        bx, by, r = rng.randint(330, 750), rng.randint(220, 330), rng.randint(80, 110)
        o.ellipse((bx - r, by - r, bx + r, by + r), fill=rng.choice([(185, 20, 30, 255), (245, 245, 245, 255)]))
        o.arc((bx - r + 30, by - r, bx + r - 30, by + r), 280, 80, fill=(255, 210, 200, 255), width=6)
        o.arc((bx - r + 30, by - r, bx + r - 30, by + r), 100, 260, fill=(255, 210, 200, 255), width=6)
    if variant == "bat":
        bat = Image.new("RGBA", (120, 520), (0, 0, 0, 0)); b = ImageDraw.Draw(bat)
        b.rounded_rectangle((40, 0, 80, 170), radius=14, fill=(40, 40, 40, 255))
        b.rounded_rectangle((10, 160, 110, 515), radius=24, fill=(225, 190, 130, 255))
        bat = bat.rotate(rng.choice([-35, 35]), expand=True, resample=Image.BICUBIC)
        O.paste(bat, (rng.choice([120, 640]), 120), bat)
    if variant == "stumps":
        sx = rng.randint(420, 560)
        for k in range(3):
            o.rounded_rectangle((sx + k * 55, 290, sx + k * 55 + 26, 690), radius=10, fill=(245, 230, 200, 255))
        o.rounded_rectangle((sx - 5, 278, sx + 70, 292), radius=6, fill=(250, 200, 0, 255))
        o.rounded_rectangle((sx + 70, 262, sx + 150, 276), radius=6, fill=(250, 200, 0, 255))
    return Image.alpha_composite(img, O)


def health(rng):
    img, _ = _bg(rng, ["teal", "navy", "maroon", "slate"])
    L = _new(); d = ImageDraw.Draw(L)
    cx, cy = _side(rng), rng.randint(300, 380)
    col = rng.choice([(235, 50, 60), (0, 200, 140), (60, 170, 255)])
    d.rounded_rectangle((cx - 60, cy - 180, cx + 60, cy + 180), radius=20, fill=col + (255,))
    d.rounded_rectangle((cx - 180, cy - 60, cx + 180, cy + 60), radius=20, fill=col + (255,))
    # heartbeat line
    y = rng.randint(560, 640)
    pts = [(0, y), (260, y), (300, y - 70), (340, y + 90), (380, y - 160), (420, y + 40), (460, y), (W, y)]
    shift = rng.randint(-150, 400)
    d.line([(x + shift if 0 < i < 7 else x, yy) for i, (x, yy) in enumerate(pts)], fill=(255, 255, 255, 230), width=8, joint="curve")
    return _glow(img, L, blur=26)


def education(rng):
    img, _ = _bg(rng, ["navy", "purple", "teal", "maroon", "green"])
    L = _new(); d = ImageDraw.Draw(L)
    cx, cy = _side(rng), rng.randint(250, 320)
    d.polygon([(cx, cy - 110), (cx + 260, cy), (cx, cy + 110), (cx - 260, cy)], fill=(25, 25, 35, 255), outline=(220, 220, 230, 255))
    d.polygon([(cx - 150, cy + 50), (cx + 150, cy + 50), (cx + 150, cy + 190), (cx - 150, cy + 190)], fill=(25, 25, 35, 255))
    d.line([(cx + 200, cy + 20), (cx + 200, cy + 200)], fill=YELLOW + (255,), width=8)
    d.ellipse((cx + 185, cy + 195, cx + 215, cy + 240), fill=YELLOW + (255,))
    # books
    bx = 120 if cx > 540 else 760
    for k in range(rng.randint(3, 5)):
        col = rng.choice([(220, 60, 60), (40, 140, 220), (240, 180, 0), (0, 170, 110), (160, 80, 200)])
        w = rng.randint(220, 280)
        d.rounded_rectangle((bx + rng.randint(-15, 15), 700 - k * 55, bx + w, 750 - k * 55), radius=8, fill=col + (255,))
    _sparkles(d, rng, 10)
    return _glow(img, L, blur=24)


def police(rng):
    img, _ = _bg(rng, ["navy", "slate", "maroon", "purple"])
    L = _new(); d = ImageDraw.Draw(L)
    # siren lights
    for x, col in [(rng.randint(80, 300), (255, 40, 50)), (rng.randint(780, 1000), (40, 110, 255))]:
        d.ellipse((x - 160, 60, x + 160, 380), fill=col + (150,))
    img = _glow(img, L, blur=70, strength=2)
    B = _new(); b = ImageDraw.Draw(B)
    cx, cy = rng.randint(380, 700), rng.randint(330, 400)
    b.polygon([(cx, cy - 210), (cx + 170, cy - 150), (cx + 160, cy + 40), (cx, cy + 200), (cx - 160, cy + 40), (cx - 170, cy - 150)],
              fill=(210, 170, 40, 255))  # shield badge
    b.ellipse((cx - 100, cy - 100, cx + 100, cy + 100), fill=(25, 40, 80, 255), outline=(255, 230, 140, 255), width=8)
    b.polygon(_star(cx, cy, 55, 22), fill=(255, 230, 140, 255))
    # tape
    tape = Image.new("RGBA", (1400, 70), (255, 210, 0, 255)); t = ImageDraw.Draw(tape)
    for k in range(0, 1400, 90):
        t.polygon([(k, 0), (k + 40, 0), (k + 10, 70), (k - 30, 70)], fill=(20, 20, 20, 255))
    tape = tape.rotate(rng.choice([-8, 8]), expand=True, resample=Image.BICUBIC)
    B.paste(tape, (-150, rng.randint(560, 620)), tape)
    return _glow(img, B, blur=16, strength=1)


def government(rng):
    img, _ = _bg(rng, ["green", "navy", "slate", "teal", "purple"])
    L = _new(); d = ImageDraw.Draw(L)
    cx = _side(rng); base = rng.randint(650, 700)
    col = (235, 240, 245, 255)
    d.rectangle((cx - 300, base - 30, cx + 300, base), fill=col)
    d.rectangle((cx - 270, base - 60, cx + 270, base - 30), fill=col)
    for k in range(8):
        x = cx - 245 + k * 70
        d.rectangle((x, base - 300, x + 26, base - 60), fill=col)
    d.polygon([(cx - 300, base - 300), (cx + 300, base - 300), (cx, base - 420)], fill=col)
    if rng.random() < 0.5:
        d.pieslice((cx - 110, base - 520, cx + 110, base - 300), 180, 360, fill=col)
    # flag
    fx = 90 if cx > 540 else 720
    d.line([(fx, 120), (fx, 640)], fill=(220, 220, 220, 255), width=8)
    d.rectangle((fx, 120, fx + 70, 300), fill=(255, 255, 255, 255))
    d.rectangle((fx + 70, 120, fx + 270, 300), fill=(1, 100, 50, 255))
    d.ellipse((fx + 110, 150, fx + 230, 270), fill=(255, 255, 255, 255))
    d.ellipse((fx + 135, 140, fx + 245, 250), fill=(1, 100, 50, 255))
    return _glow(img, L, blur=20, strength=1)


def world(rng):
    img, _ = _bg(rng, ["navy", "teal", "purple", "slate", "maroon"])
    L = _new(); d = ImageDraw.Draw(L)
    cx, cy, r = _side(rng), rng.randint(330, 400), rng.randint(220, 260)
    col = rng.choice([(90, 200, 255), (120, 255, 200), (255, 210, 120)])
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col + (255,), width=8)
    for k in (0.35, 0.7):
        d.ellipse((cx - r * k, cy - r, cx + r * k, cy + r), outline=col + (200,), width=5)
    for f in (-0.5, 0, 0.5):
        y = cy + r * f; hw = r * math.sqrt(1 - f * f)
        d.line([(cx - hw, y), (cx + hw, y)], fill=col + (200,), width=5)
    for _ in range(rng.randint(3, 5)):  # connection arcs + pins
        a, b = rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi)
        p1 = (cx + r * 0.8 * math.cos(a), cy + r * 0.8 * math.sin(a))
        p2 = (cx + r * 0.8 * math.cos(b), cy + r * 0.8 * math.sin(b))
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 - 60
        curve = [((1 - t) ** 2 * p1[0] + 2 * (1 - t) * t * mx + t * t * p2[0],
                  (1 - t) ** 2 * p1[1] + 2 * (1 - t) * t * my + t * t * p2[1]) for t in [i / 20 for i in range(21)]]
        d.line(curve, fill=YELLOW + (220,), width=4, joint="curve")
        for p in (p1, p2):
            d.ellipse((p[0] - 10, p[1] - 10, p[0] + 10, p[1] + 10), fill=YELLOW + (255,))
    return _glow(img, L, blur=24)


def aviation(rng):
    img, _ = _bg(rng, ["sky", "navy", "orange", "purple"])
    L = _new(); d = ImageDraw.Draw(L)
    for _ in range(rng.randint(3, 5)):
        x, y = rng.randint(0, W), rng.randint(450, 720)
        d.ellipse((x - 200, y - 50, x + 200, y + 50), fill=(255, 255, 255, 60))
    plane = Image.new("RGBA", (700, 400), (0, 0, 0, 0)); p = ImageDraw.Draw(plane)
    p.rounded_rectangle((40, 170, 640, 230), radius=30, fill=(245, 245, 250, 255))
    p.polygon([(280, 190), (420, 190), (250, 20), (200, 20)], fill=(220, 225, 235, 255))
    p.polygon([(280, 210), (420, 210), (250, 380), (200, 380)], fill=(220, 225, 235, 255))
    p.polygon([(60, 180), (130, 180), (60, 90), (20, 90)], fill=(220, 225, 235, 255))
    p.polygon([(640, 200), (690, 200), (640, 180)], fill=(245, 245, 250, 255))
    for k in range(8):
        p.ellipse((450 - k * 40, 188, 466 - k * 40, 204), fill=(60, 90, 140, 255))
    plane = plane.rotate(rng.randint(8, 22), expand=True, resample=Image.BICUBIC)
    if rng.random() < 0.5:
        plane = plane.transpose(Image.FLIP_LEFT_RIGHT)
    L.paste(plane, (rng.randint(100, 330), rng.randint(60, 160)), plane)
    return _glow(img, L, blur=18, strength=1)


def animal(rng):
    img, _ = _bg(rng, ["green", "olive", "teal", "amber"])
    L = _new(); d = ImageDraw.Draw(L)
    col = rng.choice([(255, 210, 120), (255, 255, 255), (255, 160, 120)])
    for _ in range(rng.randint(3, 5)):  # paw prints
        x, y, s = rng.randint(140, 940), rng.randint(140, 640), rng.uniform(0.6, 1.2)
        d.ellipse((x - 60 * s, y - 40 * s, x + 60 * s, y + 55 * s), fill=col + (230,))
        for dx, dy in [(-70, -75), (-25, -110), (25, -110), (70, -75)]:
            d.ellipse((x + (dx - 22) * s, y + (dy - 28) * s, x + (dx + 22) * s, y + (dy + 28) * s), fill=col + (230,))
    d.polygon(_star(rng.randint(200, 880), rng.randint(200, 600), 50, 22, 4), fill=(255, 255, 255, 120))
    return _glow(img, L, blur=24)


def tech(rng):
    img, _ = _bg(rng, ["purple", "navy", "teal", "slate"])
    L = _new(); d = ImageDraw.Draw(L)
    col = rng.choice([(90, 200, 255), (160, 120, 255), (0, 230, 170)])
    cx, cy = _side(rng), rng.randint(320, 400)
    if rng.random() < 0.5:  # chip
        d.rounded_rectangle((cx - 130, cy - 130, cx + 130, cy + 130), radius=24, outline=col + (255,), width=10)
        d.rounded_rectangle((cx - 70, cy - 70, cx + 70, cy + 70), radius=12, fill=col + (255,))
        for k in range(-2, 3):
            for (x2, y2, x1, y1) in [(cx + k * 45, cy - 240, cx + k * 45, cy - 130), (cx + k * 45, cy + 240, cx + k * 45, cy + 130),
                                     (cx - 300, cy + k * 45, cx - 130, cy + k * 45), (cx + 300, cy + k * 45, cx + 130, cy + k * 45)]:
                d.line([(x1, y1), (x2, y2)], fill=col + (255,), width=6)
                d.ellipse((x2 - 9, y2 - 9, x2 + 9, y2 + 9), fill=col + (255,))
    else:  # phone with signal
        d.rounded_rectangle((cx - 120, cy - 230, cx + 120, cy + 230), radius=34, outline=col + (255,), width=10)
        d.rounded_rectangle((cx - 95, cy - 190, cx + 95, cy + 180), radius=12, fill=col + (60,))
        for k in range(3):
            r = 60 + k * 50
            d.arc((cx - r, cy - 60 - r, cx + r, cy - 60 + r), 225, 315, fill=col + (255,), width=12)
        d.ellipse((cx - 14, cy - 74, cx + 14, cy - 46), fill=col + (255,))
    return _glow(img, L, blur=20)


def water(rng):
    img, _ = _bg(rng, ["sky", "teal", "navy"])
    L = _new(); d = ImageDraw.Draw(L)
    if rng.random() < 0.5:  # dry ground + drop
        for row in range(6):
            y0 = 590 + row * 45; x = -40
            while x < W:
                w_ = rng.randint(90, 170)
                d.polygon([(x, y0 + rng.randint(-8, 8)), (x + w_, y0 + rng.randint(-8, 8)),
                           (x + w_ + rng.randint(-10, 10), y0 + 45), (x + rng.randint(-10, 10), y0 + 45)],
                          fill=(110 + rng.randint(-15, 15), 78, 46, 255), outline=(38, 24, 12, 255), width=5)
                x += w_
    else:  # waves
        for k in range(5):
            y = 560 + k * 55
            pts = [(x, y + 18 * math.sin(x / 60 + k)) for x in range(0, W + 12, 12)] + [(W, H), (0, H)]
            d.polygon(pts, fill=(20 + k * 10, 110 + k * 15, 200, 200))
    cx, cy, r = _side(rng), rng.randint(280, 340), rng.randint(120, 150)
    d.ellipse((cx - r, cy - r + 60, cx + r, cy + r + 60), fill=(40, 170, 255, 255))
    d.polygon([(cx, cy - 230), (cx - r + 8, cy + 30), (cx + r - 8, cy + 30)], fill=(40, 170, 255, 255))
    d.ellipse((cx - r * 0.55, cy, cx - r * 0.2, cy + 90), fill=(170, 225, 255, 255))
    return _glow(img, L, blur=26)


def trade(rng):
    """shipping containers + ship – exports, imports, trade deals"""
    img, _ = _bg(rng, ["navy", "teal", "slate", "orange"])
    L = _new(); d = ImageDraw.Draw(L)
    base = 600
    d.polygon([(80, base), (1000, base), (930, base + 120), (150, base + 120)], fill=(30, 35, 50, 255))
    cols = [(220, 60, 50), (0, 140, 200), (240, 170, 0), (0, 160, 100), (130, 80, 200)]
    for row in range(rng.randint(2, 4)):
        x = 160
        while x < 900:
            w = rng.choice([110, 160])
            c = rng.choice(cols)
            d.rectangle((x, base - 70 - row * 70, x + w - 6, base - 4 - row * 70), fill=c + (255,))
            for k in range(x + 12, x + w - 12, 16):
                d.line([(k, base - 64 - row * 70), (k, base - 10 - row * 70)], fill=tuple(int(v * 0.7) for v in c) + (255,), width=4)
            x += w
    for k in range(4):
        y = base + 140 + k * 25
        d.line([(x_, y + 8 * math.sin(x_ / 40 + k)) for x_ in range(0, W, 12)], fill=(120, 190, 255, 140), width=4)
    return _glow(img, L, blur=16, strength=1)


def general(rng):
    img, _ = _bg(rng, ["green", "navy", "teal", "maroon", "purple", "slate"])
    L = _new(); d = ImageDraw.Draw(L)
    cx, cy = rng.randint(250, 830), rng.randint(280, 420)
    choice = rng.choice(["rings", "mic", "megaphone"])
    if choice == "rings":
        for i in range(7):
            r = 60 + i * 55
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, max(10, 90 - i * 11)), width=4)
        d.ellipse((cx - 32, cy - 32, cx + 32, cy + 32), fill=YELLOW + (255,))
    elif choice == "mic":
        d.rounded_rectangle((cx - 75, cy - 200, cx + 75, cy + 60), radius=75, fill=(230, 230, 240, 255))
        for k in range(5):
            d.line([(cx - 55, cy - 150 + k * 30), (cx + 55, cy - 150 + k * 30)], fill=(150, 155, 170, 255), width=5)
        d.arc((cx - 120, cy - 60, cx + 120, cy + 140), 0, 180, fill=(230, 230, 240, 255), width=12)
        d.line([(cx, cy + 140), (cx, cy + 250)], fill=(230, 230, 240, 255), width=12)
        d.line([(cx - 80, cy + 250), (cx + 80, cy + 250)], fill=(230, 230, 240, 255), width=12)
    else:
        d.polygon([(cx - 180, cy - 60), (cx + 120, cy - 200), (cx + 120, cy + 200), (cx - 180, cy + 60)], fill=(230, 230, 240, 255))
        d.rectangle((cx - 240, cy - 60, cx - 180, cy + 60), fill=YELLOW + (255,))
        for k in range(3):
            r = 90 + k * 60
            d.arc((cx + 120 - r, cy - r, cx + 120 + r, cy + r), -40, 40, fill=YELLOW + (230,), width=10)
    _sparkles(d, rng, 8)
    return _glow(img, L, blur=24)


def entertainment(rng):
    img, _ = _bg(rng, ["purple", "maroon", "navy"])
    L = _new(); d = ImageDraw.Draw(L)
    for x0 in rng.sample([120, 330, 540, 750, 960], 3):
        col = rng.choice([(255, 120, 220), (255, 221, 0), (120, 180, 255), (120, 255, 200)])
        tx = x0 + rng.randint(-200, 200)
        d.polygon([(x0 - 20, 0), (x0 + 20, 0), (tx + 160, 800), (tx - 160, 800)], fill=col + (70,))
        d.ellipse((x0 - 28, -20, x0 + 28, 36), fill=col + (255,))
    cx, cy = rng.randint(330, 750), rng.randint(330, 430)
    d.polygon(_star(cx, cy, rng.randint(160, 200), 80, 5, rng.uniform(-0.2, 0.2)), fill=YELLOW + (255,))
    _sparkles(d, rng, 14)
    return _glow(img, L, blur=30)


def tribute(rng):
    """candle + soft bokeh - for deaths / condolence posts"""
    img, _ = _bg(rng, ["slate", "navy", "purple", "maroon"])
    L = _new(); d = ImageDraw.Draw(L)
    for _ in range(rng.randint(14, 24)):  # bokeh
        x, y, r = rng.randint(0, W), rng.randint(0, 600), rng.randint(14, 46)
        d.ellipse((x - r, y - r, x + r, y + r), fill=rng.choice([(255, 200, 120), (255, 230, 180), (200, 200, 255)]) + (rng.randint(25, 70),))
    img = Image.alpha_composite(img, L.filter(ImageFilter.GaussianBlur(6)))
    C = _new(); c = ImageDraw.Draw(C)
    cx = _side(rng); top = rng.randint(330, 400)
    c.rounded_rectangle((cx - 70, top, cx + 70, 760), radius=16, fill=(245, 238, 225, 255))
    c.ellipse((cx - 70, top - 18, cx + 70, top + 18), fill=(255, 250, 240, 255))
    c.line([(cx, top - 10), (cx, top - 40)], fill=(40, 30, 20, 255), width=5)
    c.ellipse((cx - 26, top - 130, cx + 26, top - 30), fill=(255, 190, 60, 255))
    c.polygon([(cx, top - 175), (cx - 24, top - 90), (cx + 24, top - 90)], fill=(255, 190, 60, 255))
    c.ellipse((cx - 11, top - 95, cx + 11, top - 45), fill=(255, 250, 220, 255))
    return _glow(img, C, blur=40, strength=3)


def ribbon(rng):
    """awareness ribbon - Pinktober / breast cancer / any awareness day (pink by default)"""
    img, _ = _bg(rng, ["purple", "maroon", "navy"])
    L = _new(); d = ImageDraw.Draw(L)
    cx, cy = _side(rng), rng.randint(300, 360)
    col = rng.choice([(255, 105, 180), (255, 130, 200), (240, 80, 160)])
    w = 46
    # loop
    d.ellipse((cx - 120, cy - 220, cx + 120, cy + 40), outline=col + (255,), width=w)
    # tails crossing
    d.line([(cx - 70, cy - 10), (cx + 110, cy + 300)], fill=col + (255,), width=w)
    d.line([(cx + 70, cy - 10), (cx - 110, cy + 300)], fill=tuple(int(c * 0.85) for c in col) + (255,), width=w)
    for _ in range(rng.randint(10, 18)):
        x, y, r = rng.randint(0, W), rng.randint(0, 680), rng.randint(6, 16)
        d.ellipse((x - r, y - r, x + r, y + r), fill=col + (rng.randint(60, 140),))
    return _glow(img, L, blur=30)


def cinema(rng):
    """film reel + clapperboard - movies, actors, dramas, film legacy"""
    img, _ = _bg(rng, ["slate", "maroon", "navy", "amber"])
    L = _new(); d = ImageDraw.Draw(L)
    cx, cy, r = rng.choice([330, 750]), rng.randint(320, 380), rng.randint(170, 200)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(200, 205, 215, 255))
    d.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), fill=(40, 40, 50, 255))
    for i in range(6):
        a = i * math.pi / 3 + rng.uniform(0, 0.5)
        hx, hy = cx + r * 0.58 * math.cos(a), cy + r * 0.58 * math.sin(a)
        d.ellipse((hx - 38, hy - 38, hx + 38, hy + 38), fill=(40, 40, 50, 255))
    # film strip
    y = rng.randint(600, 660)
    d.rectangle((0, y, W, y + 90), fill=(25, 25, 30, 255))
    for x in range(10, W, 50):
        d.rectangle((x, y + 8, x + 26, y + 22), fill=(230, 230, 230, 255))
        d.rectangle((x, y + 68, x + 26, y + 82), fill=(230, 230, 230, 255))
    # clapperboard
    bx = 1080 - cx - 150
    by = rng.randint(300, 360)
    d.rectangle((bx, by, bx + 300, by + 200), fill=(30, 30, 35, 255), outline=(240, 240, 240, 255), width=6)
    d.polygon([(bx, by - 70), (bx + 300, by - 110), (bx + 300, by - 50), (bx, by - 10)], fill=(240, 240, 240, 255))
    for k in range(4):
        x0 = bx + 20 + k * 75
        d.polygon([(x0, by - 70 - k * 10), (x0 + 35, by - 75 - k * 10), (x0 + 35, by - 18 - k * 10), (x0, by - 13 - k * 10)], fill=(30, 30, 35, 255))
    return _glow(img, L, blur=24)


def music(rng):
    """microphone + music notes - songs, singers, Coke Studio, concerts"""
    img, _ = _bg(rng, ["teal", "purple", "orange", "navy"])
    L = _new(); d = ImageDraw.Draw(L)
    cx, cy = _side(rng), rng.randint(250, 300)
    d.rounded_rectangle((cx - 75, cy - 130, cx + 75, cy + 90), radius=75, fill=(210, 215, 225, 255))
    for yy in range(cy - 100, cy + 70, 22):
        d.line([(cx - 60, yy), (cx + 60, yy)], fill=(120, 125, 140, 255), width=4)
    d.arc((cx - 115, cy - 20, cx + 115, cy + 190), 0, 180, fill=(230, 230, 235, 255), width=12)
    d.rectangle((cx - 9, cy + 190, cx + 9, cy + 330), fill=(230, 230, 235, 255))
    d.rounded_rectangle((cx - 90, cy + 325, cx + 90, cy + 350), radius=10, fill=(230, 230, 235, 255))
    for _ in range(rng.randint(4, 6)):
        nx = rng.choice([rng.randint(60, cx - 180), rng.randint(cx + 180, W - 60)]) if 240 < cx < 840 else rng.randint(60, W - 60)
        ny, s = rng.randint(120, 600), rng.uniform(0.7, 1.3)
        col = rng.choice([YELLOW, (255, 120, 220), (120, 255, 220)]) + (255,)
        d.ellipse((nx - 28 * s, ny - 20 * s, nx + 28 * s, ny + 20 * s), fill=col)
        d.rectangle((nx + 20 * s, ny - 110 * s, nx + 28 * s, ny), fill=col)
        d.polygon([(nx + 20 * s, ny - 110 * s), (nx + 70 * s, ny - 80 * s), (nx + 70 * s, ny - 60 * s), (nx + 28 * s, ny - 88 * s)], fill=col)
    return _glow(img, L, blur=26)


def hospital(rng):
    """hospital building + ambulance light - doctors, hospitals, strikes, health system"""
    img, _ = _bg(rng, ["sky", "slate", "teal"])
    L = _new(); d = ImageDraw.Draw(L)
    cx = _side(rng)
    top = rng.randint(220, 280)
    d.rectangle((cx - 230, top, cx + 230, 780), fill=(225, 230, 238, 255))
    for row in range(4):
        for colm in range(5):
            x0, y0 = cx - 200 + colm * 85, top + 130 + row * 100
            d.rectangle((x0, y0, x0 + 50, y0 + 60), fill=rng.choice([(90, 150, 210), (255, 220, 120)]) + (255,))
    d.rectangle((cx - 60, top - 120, cx + 60, top + 10), fill=(255, 255, 255, 255))
    d.rectangle((cx - 15, top - 105, cx + 15, top - 5), fill=(230, 40, 50, 255))
    d.rectangle((cx - 50, top - 70, cx + 50, top - 40), fill=(230, 40, 50, 255))
    return _glow(img, L, blur=22)


def virus(rng):
    """virus particles - outbreaks, disease, dengue, polio, plague"""
    img, _ = _bg(rng, ["green", "olive", "maroon", "teal"])
    L = _new(); d = ImageDraw.Draw(L)
    col = rng.choice([(120, 255, 120), (255, 90, 90), (255, 200, 60)])
    for i in range(rng.randint(3, 5)):
        cx, cy = rng.randint(120, W - 120), rng.randint(140, 620)
        r = rng.randint(110, 170) if i == 0 else rng.randint(40, 80)
        for k in range(12):
            a = k * math.pi / 6
            x1, y1 = cx + r * math.cos(a), cy + r * math.sin(a)
            x2, y2 = cx + (r + r * 0.4) * math.cos(a), cy + (r + r * 0.4) * math.sin(a)
            d.line([(x1, y1), (x2, y2)], fill=col + (255,), width=max(4, r // 14))
            d.ellipse((x2 - r * 0.12, y2 - r * 0.12, x2 + r * 0.12, y2 + r * 0.12), fill=col + (255,))
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (220,))
    return _glow(img, L, blur=30)


def prison(rng):
    """jail bars - prisons, jails, inmates, arrests"""
    img, _ = _bg(rng, ["slate", "navy", "amber"])
    L = _new(); d = ImageDraw.Draw(L)
    x0, x1 = rng.randint(120, 260), rng.randint(820, 960)
    d.rectangle((x0 - 20, 120, x1 + 20, 150), fill=(170, 175, 185, 255))
    d.rectangle((x0 - 20, 680, x1 + 20, 710), fill=(170, 175, 185, 255))
    n = rng.randint(6, 8)
    for i in range(n):
        x = x0 + i * (x1 - x0) / (n - 1)
        d.rounded_rectangle((x - 14, 150, x + 14, 680), radius=10, fill=(200, 205, 215, 255))
    lx, ly = rng.randint(x0 + 80, x1 - 80), rng.randint(380, 460)
    d.arc((lx - 40, ly - 80, lx + 40, ly), 180, 360, fill=YELLOW + (255,), width=14)
    d.rounded_rectangle((lx - 60, ly - 30, lx + 60, ly + 70), radius=12, fill=YELLOW + (255,))
    return _glow(img, L, blur=24)


SCENES = {f.__name__: f for f in [tribute, gold, fuel, electricity, currency, tax, people, heat, wind, rain, cricket, health,
                                  education, police, government, world, aviation, animal, tech, water, trade,
                                  general, entertainment, ribbon, cinema, music, hospital, virus, prison]}

# old "theme" names -> scenes that fit them (first = best fit)
THEME_SCENES = {
    "economy": ["currency", "tax", "trade", "gold", "people"],
    "weather": ["rain", "wind", "heat"],
    "energy": ["electricity", "fuel"],
    "water": ["water"],
    "sports": ["cricket"],
    "tech": ["tech"],
    "general": ["general", "government", "world", "people"],
    "entertainment": ["entertainment", "cinema", "music"],
    "health": ["health", "hospital", "virus", "ribbon"],
}


def recent_scenes(repo_root, n=4):
    """scene names of the last n posts (news + star logs), newest last."""
    items = []
    for f in ("posted_log.json", "celebrity_log.json"):
        p = os.path.join(repo_root, f)
        if os.path.exists(p):
            try:
                items += [x for x in json.load(open(p)) if isinstance(x, dict)]
            except Exception:
                pass
    items.sort(key=lambda x: str(x.get("published") or x.get("publish_time") or x.get("date") or "").replace("T", " ")[:16])
    return [x.get("scene") or x.get("theme") for x in items[-n:]]


def today_scenes(repo_root, today):
    """scenes already used on `today` (YYYY-MM-DD) in news + star + tribute logs."""
    used = []
    for f in ("posted_log.json", "celebrity_log.json", "tribute_log.json"):
        p = os.path.join(repo_root, f)
        if os.path.exists(p):
            try:
                used += [x.get("scene") for x in json.load(open(p)) if isinstance(x, dict) and str(x.get("date", "")).startswith(today)]
            except Exception:
                pass
    return [u for u in used if u]


def render(scene, seed=None):
    rng = random.Random(seed)
    return SCENES[scene](rng).convert("RGB")
