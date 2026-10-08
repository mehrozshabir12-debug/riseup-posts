"""Topic graphics for the top area of RiseUp Pakistan posts (no photo needed)."""
import math, random
from PIL import Image, ImageDraw, ImageFilter, ImageChops

W, H = 1080, 840
GREEN = (0, 200, 110)
YELLOW = (255, 221, 0)


def _radial(c_in, c_out, cx, cy, r):
    img = Image.new("RGB", (W, H), c_out)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(r // 2))
    return Image.composite(Image.new("RGB", (W, H), c_in), img, mask)


def _glow(base, layer, blur=18, strength=2):
    g = layer.filter(ImageFilter.GaussianBlur(blur))
    for _ in range(strength):
        base = ImageChops.screen(base, g)
    return ImageChops.screen(base, layer)


def _grid(img, color=(255, 255, 255), alpha=18, step=60):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=color + (alpha,), width=1)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=color + (alpha,), width=1)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def _crescent(img, cx, cy, r, alpha=60):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, alpha))
    o = int(r * 0.28)
    d.ellipse((cx - r + o + 20, cy - r - 10, cx + r + o, cy + r - 30), fill=(0, 0, 0, 0))
    # star
    sx, sy, sr = cx + int(r * 0.55), cy - int(r * 0.25), int(r * 0.22)
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5 + 0.3
        rr = sr if i % 2 == 0 else sr * 0.42
        pts.append((sx + rr * math.cos(ang), sy + rr * math.sin(ang)))
    d.polygon(pts, fill=(255, 255, 255, alpha))
    # cut the crescent properly (punch hole)
    hole = Image.new("L", (W, H), 0)
    ImageDraw.Draw(hole).ellipse((cx - r + o + 20, cy - r - 10, cx + r + o, cy + r - 30), fill=255)
    star = Image.new("L", (W, H), 0)
    ImageDraw.Draw(star).polygon(pts, fill=255)
    a = ov.split()[3]
    a = ImageChops.subtract(a, hole)
    a = ImageChops.lighter(a, star.point(lambda v: alpha if v else 0))
    ov.putalpha(a)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def economy():
    img = _radial((10, 80, 55), (2, 14, 10), 760, 330, 520)
    img = _grid(img)
    img = _crescent(img, 860, 180, 170, alpha=45)
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    # bars
    base_y, bw, gap, x0 = 760, 70, 30, 420
    hs = [120, 180, 150, 250, 310, 400]
    tops = []
    for i, h in enumerate(hs):
        x = x0 + i * (bw + gap)
        d.rectangle((x, base_y - h, x + bw, base_y), fill=(0, 120, 70))
        d.rectangle((x, base_y - h, x + bw, base_y - h + 8), fill=GREEN)
        tops.append((x + bw // 2, base_y - h - 40))
    # rising arrow line
    pts = [(380, 700)] + tops + [(1040, 230)]
    d.line(pts, fill=GREEN, width=12, joint="curve")
    ax, ay = 1040, 230
    d.polygon([(ax + 18, ay - 30), (ax - 48, ay - 20), (ax - 10, ay + 40)], fill=GREEN)
    img = _glow(img, layer, blur=22)
    # floating coins
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    random.seed(4)
    for cx, cy, r in [(170, 520, 60), (300, 380, 38), (120, 300, 28), (260, 640, 30)]:
        od.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 205, 40, 210), outline=(255, 240, 150, 255), width=4)
        od.ellipse((cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7), outline=(200, 150, 0, 255), width=3)
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    return img


def weather():
    img = _radial((30, 60, 110), (4, 8, 20), 540, 300, 600)
    img = _grid(img, alpha=12)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    random.seed(7)
    for _ in range(120):  # rain
        x, y = random.randint(0, W), random.randint(300, H)
        d.line([(x, y), (x - 14, y + 46)], fill=(170, 200, 255, 120), width=3)
    img = Image.alpha_composite(img.convert("RGBA"), ov)
    cl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c = ImageDraw.Draw(cl)
    for (x, y, rx, ry, col) in [(250, 230, 260, 120, (120, 135, 160)), (640, 170, 320, 150, (150, 165, 190)),
                                 (880, 300, 260, 120, (110, 125, 150)), (420, 330, 300, 110, (90, 105, 130))]:
        c.ellipse((x - rx, y - ry, x + rx, y + ry), fill=col + (235,))
    cl = cl.filter(ImageFilter.GaussianBlur(10))
    img = Image.alpha_composite(img, cl).convert("RGB")
    bolt = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(bolt).polygon([(610, 330), (520, 520), (590, 520), (530, 720), (700, 470), (620, 470), (690, 330)], fill=YELLOW)
    return _glow(img, bolt, blur=26, strength=3)


def energy():
    img = _radial((90, 60, 10), (12, 8, 2), 760, 220, 520)
    img = _grid(img)
    sun = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(sun)
    d.ellipse((700, 70, 900, 270), fill=(255, 190, 40))
    for k in range(12):
        a = k * math.pi / 6
        d.line([(800 + 130 * math.cos(a), 170 + 130 * math.sin(a)), (800 + 175 * math.cos(a), 170 + 175 * math.sin(a))], fill=(255, 190, 40), width=10)
    img = _glow(img, sun, blur=30, strength=3)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    o = ImageDraw.Draw(ov)
    for i in range(3):  # solar panels in perspective
        x0, y0 = 120 + i * 300, 520 + i * 20
        quad = [(x0, y0), (x0 + 260, y0 - 40), (x0 + 300, y0 + 150), (x0 + 30, y0 + 200)]
        o.polygon(quad, fill=(20, 50, 110, 255), outline=(170, 200, 255, 255))
        for t in (1 / 3, 2 / 3):
            a = (quad[0][0] + (quad[1][0] - quad[0][0]) * t, quad[0][1] + (quad[1][1] - quad[0][1]) * t)
            b = (quad[3][0] + (quad[2][0] - quad[3][0]) * t, quad[3][1] + (quad[2][1] - quad[3][1]) * t)
            o.line([a, b], fill=(170, 200, 255, 255), width=3)
        a = ((quad[0][0] + quad[3][0]) / 2, (quad[0][1] + quad[3][1]) / 2)
        b = ((quad[1][0] + quad[2][0]) / 2, (quad[1][1] + quad[2][1]) / 2)
        o.line([a, b], fill=(170, 200, 255, 255), width=3)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


THEMES = {"economy": economy, "weather": weather, "energy": energy}


def make(theme, path):
    THEMES[theme]().save(path, quality=95)
    return path


def water():
    img = _radial((20, 90, 150), (2, 10, 22), 560, 300, 560)
    img = _grid(img, alpha=12)
    random.seed(11)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # cracked dry ground
    d.rectangle((0, 580, W, H), fill=(38, 24, 12, 255))
    for row in range(6):
        y0 = 590 + row * 45
        x = -40
        while x < W:
            w_ = random.randint(90, 170)
            d.polygon([(x, y0 + random.randint(-8, 8)), (x + w_, y0 + random.randint(-8, 8)),
                       (x + w_ + random.randint(-10, 10), y0 + 45 + random.randint(-8, 8)),
                       (x + random.randint(-10, 10), y0 + 45 + random.randint(-8, 8))],
                      fill=(110 + random.randint(-15, 15), 78, 46, 255), outline=(38, 24, 12, 255), width=5)
            x += w_
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    # glowing water drop
    drop = Image.new("RGB", (W, H), (0, 0, 0))
    dd = ImageDraw.Draw(drop)
    cx, cy, r = 540, 330, 150
    dd.ellipse((cx - r, cy - r + 60, cx + r, cy + r + 60), fill=(40, 170, 255))
    dd.polygon([(cx, cy - 230), (cx - r + 8, cy + 30), (cx + r - 8, cy + 30)], fill=(40, 170, 255))
    dd.ellipse((cx - 85, cy - 10, cx - 35, cy + 90), fill=(170, 225, 255))
    img = _glow(img, drop, blur=30, strength=2)
    return img


THEMES["water"] = water


def general():
    img = _radial((0, 95, 55), (2, 16, 10), 700, 260, 560)
    img = _grid(img)
    img = _crescent(img, 760, 330, 230, alpha=70)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for i in range(7):  # news "signal" rings
        r = 60 + i * 55
        d.ellipse((180 - r, 300 - r, 180 + r, 300 + r), outline=(255, 255, 255, max(10, 70 - i * 9)), width=4)
    d.ellipse((150, 270, 210, 330), fill=(255, 221, 0, 255))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def sports():
    img = _radial((10, 70, 40), (2, 10, 6), 540, 820, 700)
    lights = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(lights)
    for x in (140, 940):
        for k in range(3):
            for j in range(4):
                d.ellipse((x - 70 + j * 36, 80 + k * 34, x - 50 + j * 36, 100 + k * 34), fill=(255, 250, 220))
    img = _glow(img, lights, blur=28, strength=3)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    o = ImageDraw.Draw(ov)
    o.polygon([(0, 840), (300, 420), (780, 420), (1080, 840)], fill=(30, 120, 50, 255))
    o.polygon([(470, 840), (500, 430), (580, 430), (610, 840)], fill=(200, 175, 120, 255))
    # cricket ball
    o.ellipse((440, 200, 640, 400), fill=(185, 20, 30, 255))
    o.arc((470, 200, 610, 400), 280, 80, fill=(255, 235, 220, 255), width=6)
    o.arc((470, 200, 610, 400), 100, 260, fill=(255, 235, 220, 255), width=6)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def tech():
    img = _radial((40, 20, 110), (4, 3, 18), 540, 330, 600)
    img = _grid(img, color=(120, 160, 255), alpha=22, step=48)
    layer = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    random.seed(3)
    cx, cy = 540, 360
    d.rounded_rectangle((cx - 130, cy - 130, cx + 130, cy + 130), radius=24, outline=(90, 200, 255), width=10)
    d.rounded_rectangle((cx - 70, cy - 70, cx + 70, cy + 70), radius=12, fill=(90, 200, 255))
    for k in range(-2, 3):
        for (x1, y1, x2, y2) in [(cx + k * 45, cy - 130, cx + k * 45, cy - 240), (cx + k * 45, cy + 130, cx + k * 45, cy + 240),
                                 (cx - 130, cy + k * 45, cx - 300, cy + k * 45), (cx + 130, cy + k * 45, cx + 300, cy + k * 45)]:
            d.line([(x1, y1), (x2, y2)], fill=(90, 200, 255), width=6)
            d.ellipse((x2 - 9, y2 - 9, x2 + 9, y2 + 9), fill=(90, 200, 255))
    return _glow(img, layer, blur=20, strength=2)


THEMES.update({"general": general, "sports": sports, "tech": tech})
