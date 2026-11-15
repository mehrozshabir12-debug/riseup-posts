"""RiseUp Pakistan — attention-grabbing Reel cover (owner's rule, 15 Nov 2026).

Every Reel posted on RiseUp gets one of these as its cover (Metricool videoThumbnailUrl).

Usage:
  python make_reel_cover.py VIDEO.mp4 OUT.jpg "Hook Headline" \
      --hl "Word1,Word2" --sub "One line that says what the reel is" \
      --tag "DRAMA CLIP" [--credit "@basharat.137"] [--t 12.5] [--edited]

- VIDEO can be the original clip, or the edited RiseUp reel with --edited
  (then only the sharp top part of the reel is used for the picture).
- The sharpest, brightest frame (face preferred) is picked automatically; --t forces a time.
- Layout 1080x1920. Everything important sits inside the Instagram grid crop
  (3:4, y 240-1680) so the cover still reads on the profile grid.
  * RiseUp logo + "RISEUP / PAKISTAN" top-left, yellow tag pill top-right
  * big Poppins Black headline (UPPERCASE, max 3 lines); --hl words in a yellow box
  * short white description line, yellow "PURA DEKHEIN" button
  * credit line, FB | IG | TikTok icons and @riseuppakistann at the bottom
  * thin yellow border round the whole cover
"""
import argparse, json, os, subprocess, tempfile
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
F = os.path.join(HERE, "fonts")
W, H = 1080, 1920
YEL = (255, 204, 0)
SAFE_TOP, SAFE_BOT = 240, 1680


def font(name, size):
    return ImageFont.truetype(os.path.join(F, name), size)


def probe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height:format=duration", "-of", "json", path])
    j = json.loads(out)
    return j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])


def grab(path, t):
    with tempfile.NamedTemporaryFile(suffix=".png") as tf:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", tf.name],
                       check=True)
        return cv2.imread(tf.name)


_face = None


def faces(img):
    """Face boxes if OpenCV's face model is available, else [] (frame pick still works)."""
    global _face
    if _face is None:
        _face = False
        for base in (getattr(getattr(cv2, "data", None), "haarcascades", ""), "/usr/share/opencv4/haarcascades/",
                     "/usr/share/opencv/haarcascades/"):
            p = os.path.join(base, "haarcascade_frontalface_default.xml")
            if base and os.path.exists(p):
                c = cv2.CascadeClassifier(p)
                if not c.empty():
                    _face = c
                    break
    if _face is False:
        return []
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return _face.detectMultiScale(g, 1.15, 6, minSize=(img.shape[1] // 10, img.shape[1] // 10))


def crop_edited(fr):
    # edited reel: sharp video is at the top, headline/shade from ~y1100 down; drop logo strip too
    h = fr.shape[0]
    return fr[int(h * 0.11):int(h * 0.56)]


def pick_frame(path, dur, t=None, edited=False):
    if t is not None:
        fr = grab(path, t)
        return crop_edited(fr) if edited else fr
    end = dur - (3.2 if edited else 0.3)  # skip RiseUp outro on edited reels
    best, bs = None, -1
    for k in range(18):
        tt = max(0.3, dur * 0.08 + (end - dur * 0.08) * k / 17)
        fr = grab(path, min(tt, end))
        if fr is None:
            continue
        if edited:
            fr = crop_edited(fr)
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        sharp = cv2.Laplacian(g, cv2.CV_64F).var()
        bright = g.mean()
        score = np.log1p(sharp) * (1 - abs(bright - 115) / 160)
        fc = faces(fr)
        if len(fc):
            score *= 1.6
        if score > bs:
            best, bs = fr, score
    return best


def cover_bg(fr):
    """Fill 1080x1920 with the frame. Portrait frames fill it; landscape frames get a
    blurred fill and the sharp picture centred on the face, upper half."""
    img = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(1.15)
    w, h = img.size
    fc = faces(fr)
    cx = (fc[0][0] + fc[0][2] / 2) / w if len(fc) else 0.5
    if h / w >= 1.2:  # portrait: cover-crop, keep face
        s = max(W / w, H / h)
        im = img.resize((int(w * s + 1), int(h * s + 1)), Image.LANCZOS)
        x = int(min(max(cx * im.width - W / 2, 0), im.width - W))
        return im.crop((x, 0, x + W, H)).convert("RGBA")
    # landscape / square: blurred background + big sharp crop on top
    s = H / h
    bg = img.resize((int(w * s + 1), H), Image.LANCZOS)
    x = int((bg.width - W) / 2)
    bg = bg.crop((x, 0, x + W, H)).filter(ImageFilter.GaussianBlur(40))
    bg = ImageEnhance.Brightness(bg).enhance(0.45).convert("RGBA")
    th = 1320  # sharp area height (zoomed to fill the top part)
    s2 = max(W / w, th / h)
    sh = img.resize((int(w * s2 + 1), int(h * s2 + 1)), Image.LANCZOS)
    x = int(min(max(cx * sh.width - W / 2, 0), sh.width - W))
    sh = sh.crop((x, 0, x + W, min(th, sh.height))).convert("RGBA")
    m = Image.new("L", sh.size, 255)
    md = ImageDraw.Draw(m)
    for i in range(220):
        md.line([(0, sh.height - 220 + i), (W, sh.height - 220 + i)], fill=int(255 * (1 - i / 220)))
    bg.paste(sh, (0, 0), m)
    return bg


def shades(img):
    g = np.zeros((H, W, 4), np.uint8)
    for y in range(0, 420):
        g[y, :, 3] = int(190 * (1 - y / 420) ** 1.6)
    y0 = 860
    for y in range(y0, H):
        t = min(1, (y - y0) / 640)
        g[y, :, 3] = max(g[y, 0, 3], int(250 * t ** 1.1))
    # soft side vignette
    xs = np.abs(np.arange(W) - W / 2) / (W / 2)
    v = (np.clip(xs - 0.6, 0, 1) / 0.4 * 90).astype(np.uint8)
    g[:, :, 3] = np.maximum(g[:, :, 3], v[None, :])
    return Image.alpha_composite(img, Image.fromarray(g, "RGBA"))


def icons_row(img, cy, scale=0.62, gap=30):
    d = ImageDraw.Draw(img)
    ics = []
    for n in ("icon_facebook.png", "icon_instagram.png", "icon_tiktok.png"):
        ic = Image.open(os.path.join(A, n)).convert("RGBA")
        ics.append(ic.resize((int(ic.width * scale), int(ic.height * scale)), Image.LANCZOS))
    hf = font("Poppins-Bold.ttf", 34)
    handle = "@riseuppakistann"
    total = sum(i.width for i in ics) + gap * 2 * len(ics) + d.textlength(handle, font=hf)
    x = (W - total) / 2
    for ic in ics:
        img.alpha_composite(ic, (int(x), int(cy - ic.height / 2)))
        x += ic.width + gap
        d.line([(x, cy - 20), (x, cy + 20)], fill=(255, 255, 255, 200), width=3)
        x += gap
    d.text((x, cy), handle, font=hf, fill="white", anchor="lm")


def text_tracked(d, xy, s, fnt, fill, track=-3, stroke=0, stroke_fill=None):
    x, y = xy
    for c in s:
        d.text((x, y), c, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
        x += d.textlength(c, font=fnt) + track
    return x


def tracked_len(d, s, fnt, track=-3):
    return sum(d.textlength(c, font=fnt) + track for c in s) - track


def layout_headline(d, words, size, maxw, track):
    hf = font("Poppins-Black.ttf", size)
    sp = d.textlength(" ", font=hf) * 0.75
    lines, cur, cw = [], [], 0
    for w in words:
        wl = tracked_len(d, w, hf, track) + 28  # room for yellow box padding
        add = wl + (sp if cur else 0)
        if cur and cw + add > maxw:
            lines.append(cur); cur, cw = [w], wl
        else:
            cur.append(w); cw += add
    if cur:
        lines.append(cur)
    return hf, sp, lines


def build(fr, title, hl, sub, tag, credit):
    img = shades(cover_bg(fr))
    d = ImageDraw.Draw(img)

    # --- top: logo + wordmark (left), tag pill (right) — inside grid safe zone
    logo = Image.open(os.path.join(A, "logo_white.png")).convert("RGBA")
    lh = 96
    logo = logo.resize((int(logo.width * lh / logo.height), lh), Image.LANCZOS)
    ty = SAFE_TOP + 34
    img.alpha_composite(logo, (58, ty))
    wf = font("Poppins-Bold.ttf", 34)
    d.text((58 + logo.width + 14, ty + 12), "RISEUP", font=wf, fill="white")
    d.text((58 + logo.width + 14, ty + 48), "PAKISTAN", font=wf, fill="white")
    if tag:
        pf = font("Poppins-Black.ttf", 34)
        t = tag.upper()
        tw = d.textlength(t, font=pf)
        x1, y1 = W - 58, ty + 18
        x0 = x1 - tw - 56
        d.rounded_rectangle([x0, y1, x1, y1 + 62], radius=31, fill=YEL)
        d.text(((x0 + x1) / 2, y1 + 31), t, font=pf, fill=(0, 0, 0), anchor="mm")

    # --- headline (uppercase, auto size, max 3 lines)
    words = title.upper().split()
    hlset = {w.upper().strip(",.!?:'\"") for w in hl}
    track = -3
    for size in (138, 128, 118, 108, 98, 90, 82):
        hf, sp, lines = layout_headline(d, words, size, 960, track)
        if len(lines) <= 3:
            break
    lh_px = int(size * 1.02)
    sf = font("Poppins-Bold.ttf", 44)
    sub_lines = []
    if sub:
        cur = []
        for w in sub.split():
            if cur and d.textlength(" ".join(cur + [w]), font=sf) > 900:
                sub_lines.append(" ".join(cur)); cur = [w]
            else:
                cur.append(w)
        sub_lines.append(" ".join(cur))
        sub_lines = sub_lines[:2]
    btn_h = 92
    block = lh_px * len(lines) + (24 + 58 * len(sub_lines) if sub_lines else 0) + 40 + btn_h
    y = SAFE_BOT - 30 - block
    for ln in lines:
        tw = sum(tracked_len(d, w, hf, track) + (28 if w.strip(",.!?:'\"") in hlset else 0) for w in ln) \
            + sp * (len(ln) - 1)
        x = (W - tw) / 2
        for w in ln:
            core = w.strip(",.!?:'\"")
            wl = tracked_len(d, w, hf, track)
            if core in hlset:
                bx0, by0 = x, y + size * 0.13
                d.rounded_rectangle([bx0, by0, bx0 + wl + 28, by0 + size * 0.98], radius=12, fill=YEL)
                text_tracked(d, (x + 14, y), w, hf, (0, 0, 0), track)
                x += wl + 28 + sp
            else:
                text_tracked(d, (x, y), w, hf, (255, 255, 255), track, stroke=3, stroke_fill=(0, 0, 0))
                x += wl + sp
        y += lh_px
    if sub_lines:
        y += 24
        for s in sub_lines:
            d.text((W / 2, y + 26), s, font=sf, fill=(235, 235, 235), anchor="mm")
            y += 58
    # --- button
    y += 40
    bf = font("Poppins-Black.ttf", 40)
    bt = "PURA DEKHEIN"
    bw = d.textlength(bt, font=bf) + 150
    bx0 = (W - bw) / 2
    d.rounded_rectangle([bx0, y, bx0 + bw, y + btn_h], radius=46, fill=YEL)
    cx, cy = bx0 + 62, y + btn_h / 2
    d.polygon([(cx - 14, cy - 19), (cx - 14, cy + 19), (cx + 20, cy)], fill=(0, 0, 0))
    d.text((bx0 + 96, cy), bt, font=bf, fill=(0, 0, 0), anchor="lm")

    # --- bottom: credit + icons/handle (outside grid crop, visible in full view)
    if credit:
        cf = font("Poppins-Regular.ttf", 32)
        d.text((W / 2, 1752), f"Credit: {credit}", font=cf, fill=(210, 210, 210), anchor="mm")
    icons_row(img, 1836)

    # --- thin yellow border
    th = 8
    d.rectangle([0, 0, W - 1, th - 1], fill=YEL); d.rectangle([0, H - th, W - 1, H - 1], fill=YEL)
    d.rectangle([0, 0, th - 1, H - 1], fill=YEL); d.rectangle([W - th, 0, W - 1, H - 1], fill=YEL)
    return img.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("out"); ap.add_argument("title")
    ap.add_argument("--hl", default="")
    ap.add_argument("--sub", default="")
    ap.add_argument("--tag", default="")
    ap.add_argument("--credit", default="")
    ap.add_argument("--t", type=float, default=None)
    ap.add_argument("--edited", action="store_true")
    a = ap.parse_args()
    _, _, dur = probe(a.video)
    fr = pick_frame(a.video, dur, a.t, a.edited)
    img = build(fr, a.title, [w for w in a.hl.split(",") if w], a.sub, a.tag, a.credit)
    img.save(a.out, quality=92, optimize=True)
    print("cover:", a.out)


if __name__ == "__main__":
    main()
