"""RiseUp Pakistan news post template (1080x1350, 4:5).

Usage:
  python3 make_post.py config.json out.png

config.json keys:
  scene      top graphic: gold, fuel, electricity, currency, tax, people, heat, wind, rain, cricket,
             health, education, police, government, world, aviation, animal, tech, water, trade,
             general, entertainment  (drawn with a random seed, so it looks different every time)
  seed       optional, to reproduce an exact image
  theme      old name (economy, weather, ...) - used only when no scene is given
  photo      path to a top photo instead of a scene
  line1      headline line on yellow bar (black text)   e.g. "Remittances Surge"
  line2      big white headline line                     e.g. "To $3.63 Billion"
  sub        white sub-headline text                     e.g. "Pakistan records strong workers' inflows"
  sub_hl     last part of sub-headline on yellow bar     e.g. "in July 2026"
  tag        small label under the yellow rule           e.g. "Official finance update"
"""
import json, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
A = lambda f: os.path.join(HERE, "assets", f)
W, H = 1080, 1350
YELLOW = (255, 221, 0)
BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
REG = "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf"
MX = 52                      # side margin
PHOTO_H = 840                # photo area height (fades into black)


def font(path, size):
    return ImageFont.truetype(path, size)


def text_w(d, t, f, sw):
    b = d.textbbox((0, 0), t, font=f, stroke_width=sw)
    return b[2] - b[0]


def fit(d, t, path, max_w, start, minimum, sw_ratio=0.016):
    s = start
    while s > minimum:
        f = font(path, s)
        if text_w(d, t, f, int(s * sw_ratio)) <= max_w:
            return f, int(s * sw_ratio)
        s -= 2
    return font(path, minimum), int(minimum * sw_ratio)


def draw_text(d, xy, t, f, sw, fill):
    # stroke in the same colour thickens Poppins Bold toward ExtraBold
    d.text(xy, t, font=f, fill=fill, stroke_width=sw, stroke_fill=fill)


def cover(img, w, h):
    r = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    l = (img.width - w) // 2
    t = max(0, (img.height - h) // 3)  # keep upper part (faces/sky) in view
    return img.crop((l, t, l + w, t + h))


def wrap(d, words, f, sw, max_w):
    lines, cur = [], ""
    for w_ in words:
        test = (cur + " " + w_).strip()
        if text_w(d, test, f, sw) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur); cur = w_
    if cur:
        lines.append(cur)
    return lines


def render(cfg, out):
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    if cfg.get("photo"):
        src = Image.open(cfg["photo"]).convert("RGB")
    else:
        import random as _r, scenes
        recent = scenes.recent_scenes(os.path.dirname(HERE), 4)
        scene = cfg.get("scene")
        if not scene:  # old-style config: pick a fitting scene not used recently
            opts = scenes.THEME_SCENES.get(cfg.get("theme", "general"), ["general"])
            fresh = [o for o in opts if o not in recent]
            scene = (fresh or opts)[0]
        import datetime as _dt
        _today = (_dt.datetime.utcnow() + _dt.timedelta(hours=5)).strftime("%Y-%m-%d")
        if scene in scenes.today_scenes(os.path.dirname(HERE), _today):
            print(f"WARNING: scene '{scene}' was ALREADY USED TODAY - owner rule: pick a different scene that fits the story")
        if scene in recent[-3:]:
            print(f"WARNING: scene '{scene}' was used in the last 3 posts {recent[-3:]} - pick another if it fits")
        seed = cfg.get("seed") or _r.randrange(10**9)
        src = scenes.render(scene, seed)
        print(f"scene={scene} seed={seed}")
    photo = cover(src, W, PHOTO_H)
    canvas.paste(photo, (0, 0))

    # fade photo into black
    grad = Image.new("L", (W, H), 0)
    gd = ImageDraw.Draw(grad)
    fade_start, fade_end = 470, PHOTO_H
    for y in range(fade_start, H):
        v = 255 if y >= fade_end else int(255 * ((y - fade_start) / (fade_end - fade_start)) ** 1.4)
        gd.line([(0, y), (W, y)], fill=v)
    canvas = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), canvas, grad)

    # soft dark corner behind the logo for readability
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).ellipse((-220, -200, 520, 300), fill=120)
    sh = sh.filter(ImageFilter.GaussianBlur(70))
    canvas = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), canvas, sh)

    d = ImageDraw.Draw(canvas)

    # logo + wordmark
    logo = Image.open(A("logo_white.png"))
    lh = 112
    logo = logo.resize((round(logo.width * lh / logo.height), lh), Image.LANCZOS)
    canvas.paste(logo, (MX, 40), logo)
    wf = font(BOLD, 38)
    draw_text(d, (MX + logo.width + 14, 52), "RISEUP", wf, 0, (255, 255, 255))
    draw_text(d, (MX + logo.width + 14, 94), "PAKISTAN", wf, 0, (255, 255, 255))

    max_w = W - 2 * MX - 30

    if cfg.get("style") == "bold":
        render_bold(canvas, d, cfg)
        canvas.save(out, quality=95)
        return

    # line 1 on yellow bar
    f1, sw1 = fit(d, cfg["line1"], BOLD, max_w, 98, 60)
    b = d.textbbox((0, 0), cfg["line1"], font=f1, stroke_width=sw1)
    tw, th = b[2] - b[0], b[3] - b[1]
    pad_x, pad_y = 18, 14
    y = 700
    d.rectangle((MX, y, MX + tw + 2 * pad_x, y + th + 2 * pad_y), fill=YELLOW)
    draw_text(d, (MX + pad_x - b[0], y + pad_y - b[1]), cfg["line1"], f1, sw1, (0, 0, 0))
    y += th + 2 * pad_y + 20

    # line 2 big white
    f2, sw2 = fit(d, cfg["line2"], BOLD, max_w + 30, 116, 64)
    b = d.textbbox((0, 0), cfg["line2"], font=f2, stroke_width=sw2)
    draw_text(d, (MX - b[0], y - b[1]), cfg["line2"], f2, sw2, (255, 255, 255))
    y += (b[3] - b[1]) + 30

    # sub headline (white) + highlighted tail on yellow, wrapped
    fs = font(BOLD, 56); sws = 1
    words = cfg["sub"].split()
    hl = cfg.get("sub_hl", "").strip()
    lines = wrap(d, words, fs, sws, max_w)
    hl_w = text_w(d, hl, fs, sws) + 30 if hl else 0
    gap = 14
    asc = d.textbbox((0, 0), "Hg", font=fs, stroke_width=sws)
    lh_ = asc[3] - asc[1]
    for i, ln in enumerate(lines):
        draw_text(d, (MX, y - asc[1]), ln, fs, sws, (255, 255, 255))
        last = i == len(lines) - 1
        if last and hl:
            lw = text_w(d, ln, fs, sws)
            if MX + lw + 20 + hl_w <= W - MX:
                hx, hy = MX + lw + 20, y
            else:
                y += lh_ + gap; hx, hy = MX, y
            d.rectangle((hx, hy - 8, hx + hl_w, hy + lh_ + 10), fill=YELLOW)
            draw_text(d, (hx + 15, hy - asc[1]), hl, fs, sws, (0, 0, 0))
        y += lh_ + gap
    if not lines and hl:
        pass

    # yellow rule + tag
    y += 18
    d.rectangle((MX, y, MX + 140, y + 6), fill=YELLOW)
    y += 26
    tf = font(REG, 36)
    d.text((MX, y), cfg.get("tag", ""), font=tf, fill=(255, 255, 255))

    # social icons: Facebook | Instagram | TikTok (no X)
    icons = [Image.open(A(f"icon_{n}.png")) for n in ("facebook", "instagram", "tiktok")]
    ih = 46
    icons = [i.resize((round(i.width * ih / i.height), ih), Image.LANCZOS) for i in icons]
    sep_gap = 34
    total = sum(i.width for i in icons) + sep_gap * 2 * (len(icons) - 1)
    x = (W - total) // 2
    iy = H - 96
    for k, ic in enumerate(icons):
        canvas.paste(ic, (x, iy), ic)
        x += ic.width
        if k < len(icons) - 1:
            x += sep_gap
            d.line([(x, iy - 4), (x, iy + ih + 4)], fill=(230, 230, 230), width=2)
            x += sep_gap

    canvas.save(out, quality=95)


def render_bold(canvas, d, cfg):
    """'bold' news style: centred UPPERCASE headline with a yellow-boxed key word, yellow rules,
    kicker, short description, SOURCE line and icons.
    cfg: head1, head2_hl (yellow box), head2 (white after the box), kicker, desc, source, date"""
    max_w = W - 2 * MX
    y = 690
    h1 = cfg["head1"].upper()
    f1, sw1 = fit(d, h1, BOLD, max_w, 104, 60)
    b = d.textbbox((0, 0), h1, font=f1, stroke_width=sw1)
    draw_text(d, ((W - (b[2] - b[0])) // 2 - b[0], y - b[1]), h1, f1, sw1, (255, 255, 255))
    y += (b[3] - b[1]) + 34
    hl, rest = cfg.get("head2_hl", "").upper(), cfg.get("head2", "").upper()
    size = f1.size
    while size > 56:
        f2 = font(BOLD, size); sw2 = int(size * 0.016)
        wh = text_w(d, hl, f2, sw2) + 40 if hl else 0
        wr = text_w(d, rest, f2, sw2) if rest else 0
        if wh + (24 if hl and rest else 0) + wr <= max_w:
            break
        size -= 2
    asc = d.textbbox((0, 0), "HG", font=f2, stroke_width=sw2)
    th = asc[3] - asc[1]
    x = (W - (wh + (24 if hl and rest else 0) + wr)) // 2
    if hl:
        d.rectangle((x, y - 16, x + wh, y + th + 16), fill=YELLOW)
        draw_text(d, (x + 20, y - asc[1]), hl, f2, sw2, (0, 0, 0))
        x += wh + 24
    if rest:
        draw_text(d, (x, y - asc[1]), rest, f2, sw2, (255, 255, 255))
    y += th + 40
    d.rectangle((MX + 10, y, MX + 170, y + 6), fill=YELLOW)
    y += 28
    if cfg.get("kicker"):
        k = cfg["kicker"].upper()
        fk, swk = fit(d, k, BOLD, max_w, 62, 40)
        b = d.textbbox((0, 0), k, font=fk, stroke_width=swk)
        draw_text(d, ((W - (b[2] - b[0])) // 2 - b[0], y - b[1]), k, fk, swk, (255, 255, 255))
        y += (b[3] - b[1]) + 26
    if cfg.get("desc"):
        fd = font(REG, 42)
        for ln in wrap(d, cfg["desc"].split(), fd, 0, max_w - 60)[:2]:
            b = d.textbbox((0, 0), ln, font=fd)
            d.text(((W - (b[2] - b[0])) // 2 - b[0], y - b[1]), ln, font=fd, fill=(240, 240, 240))
            y += 54
    y += 14
    d.rectangle((MX + 10, y, MX + 170, y + 6), fill=YELLOW)
    y += 26
    src = cfg.get("source", "")
    if src:
        fsb, fsr = font(BOLD, 34), font(REG, 34)
        tail = " " + src.upper() + (" • " + cfg["date"].upper() if cfg.get("date") else "")
        d.text((MX + 10, y), "SOURCE:", font=fsb, fill=(255, 255, 255))
        d.text((MX + 10 + d.textlength("SOURCE:", font=fsb), y), tail, font=fsr, fill=(255, 255, 255))
    # icons (same as classic)
    icons = [Image.open(A(f"icon_{n}.png")) for n in ("facebook", "instagram", "tiktok")]
    ih = 46
    icons = [i.resize((round(i.width * ih / i.height), ih), Image.LANCZOS) for i in icons]
    gap = 34
    total = sum(i.width for i in icons) + gap * 2 * (len(icons) - 1)
    x = (W - total) // 2; iy = H - 82
    for k_, ic in enumerate(icons):
        canvas.paste(ic, (x, iy), ic); x += ic.width
        if k_ < len(icons) - 1:
            x += gap; d.line([(x, iy - 4), (x, iy + ih + 4)], fill=(230, 230, 230), width=2); x += gap


if __name__ == "__main__":
    render(json.load(open(sys.argv[1])), sys.argv[2])
    print("saved", sys.argv[2])
