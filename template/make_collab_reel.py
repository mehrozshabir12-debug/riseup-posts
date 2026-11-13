"""RiseUp approved collab reel design (13 Nov 2026, "Wusat v2" look).

Usage:
  python make_collab_reel.py SRC.mp4 OUT.mp4 "Headline Words Here" --hl "Word1,Word2" [--shift 0]

- 1080x1920, source video fills the width; --shift moves it up (px) and the gap
  below is filled with a blurred, darkened copy joined by a soft fade.
- RiseUp logo + wordmark top-left, dark top gradient.
- Heavy Poppins Black headline (white, highlighted words yellow) in a tight
  centred block near the bottom on a black shade; stays the whole video.
- FB / IG / TikTok icons at the bottom.
- Thin yellow border travels clockwise round all four edges start -> end.
- 0.5 s fade to black, then 2.5 s black outro: logo, wordmark, yellow bar, icons.
- Source audio kept as-is.
"""
import argparse, os, subprocess, json
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
F = os.path.join(HERE, "fonts")
W, H = 1080, 1920
YEL = (255, 204, 0)
FPS = 30
OUTRO, FADE = 2.5, 0.5


def font(name, size):
    return ImageFont.truetype(os.path.join(F, name), size)


def icons_row(img, cy, scale=1.0, gap=46):
    names = ["icon_facebook.png", "icon_instagram.png", "icon_tiktok.png"]
    ics = []
    for n in names:
        ic = Image.open(os.path.join(A, n)).convert("RGBA")
        ics.append(ic.resize((int(ic.width * scale), int(ic.height * scale)), Image.LANCZOS))
    total = sum(i.width for i in ics) + gap * 2 * (len(ics) - 1)
    x = (W - total) // 2
    d = ImageDraw.Draw(img)
    for k, ic in enumerate(ics):
        img.alpha_composite(ic, (x, cy - ic.height // 2))
        x += ic.width
        if k < len(ics) - 1:
            lx = x + gap
            d.line([(lx, cy - int(28 * scale)), (lx, cy + int(28 * scale))], fill=(255, 255, 255, 255), width=3)
            x += gap * 2


def wrap(words, fnt, maxw, d):
    lines, cur = [], []
    for w in words:
        t = " ".join(cur + [w])
        if cur and d.textlength(t, font=fnt) > maxw:
            lines.append(cur); cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def overlay(headline, hl_words):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = np.zeros((H, W, 4), np.uint8)
    # top shade
    for y in range(0, 300):
        g[y, :, 3] = int(150 * (1 - y / 300) ** 1.5)
    # bottom black shade behind headline
    y0 = 1100
    for y in range(y0, H):
        t = min(1, (y - y0) / 520)
        g[y, :, 3] = int(255 * min(1, t ** 1.2 * 1.05))
    img = Image.alpha_composite(img, Image.fromarray(g, "RGBA"))
    # logo + wordmark
    logo = Image.open(os.path.join(A, "logo_white.png")).convert("RGBA")
    lh = 112
    logo = logo.resize((int(logo.width * lh / logo.height), lh), Image.LANCZOS)
    img.alpha_composite(logo, (52, 56))
    d = ImageDraw.Draw(img)
    wf = font("Poppins-Bold.ttf", 38)
    d.text((148, 76), "RISEUP", font=wf, fill="white")
    d.text((148, 116), "PAKISTAN", font=wf, fill="white")
    # headline
    hf = font("Poppins-Black.ttf", 96)
    track = -4
    hl = {w.lower().strip(",.!?") for w in hl_words}
    words = headline.split()

    def wlen(w):
        return sum(d.textlength(c, font=hf) + track for c in w) - track

    sp = d.textlength(" ", font=hf) - 6
    lines, cur, cw = [], [], 0
    for w in words:
        add = wlen(w) + (sp if cur else 0)
        if cur and cw + add > 900:
            lines.append(cur); cur, cw = [w], wlen(w)
        else:
            cur.append(w); cw += add
    if cur:
        lines.append(cur)
    lh = 94
    bottom = 1715
    top = bottom - lh * len(lines)
    for i, ln in enumerate(lines):
        tw = sum(wlen(w) for w in ln) + sp * (len(ln) - 1)
        x = (W - tw) / 2
        y = top + i * lh
        for w in ln:
            col = YEL if w.lower().strip(",.!?") in hl else (255, 255, 255)
            for c in w:
                d.text((x, y), c, font=hf, fill=col)
                x += d.textlength(c, font=hf) + track
            x += sp - track
    icons_row(img, 1866)
    return img


def outro_img():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    logo = Image.open(os.path.join(A, "logo_white.png")).convert("RGBA")
    lh = 310
    logo = logo.resize((int(logo.width * lh / logo.height), lh), Image.LANCZOS)
    img.alpha_composite(logo, ((W - logo.width) // 2, 610))
    d = ImageDraw.Draw(img)
    f = font("Poppins-Bold.ttf", 84)
    for t, y in (("RISEUP", 975), ("PAKISTAN", 1068)):
        d.text(((W - d.textlength(t, font=f)) / 2, y), t, font=f, fill="white")
    d.rectangle([448, 1186, 632, 1193], fill=YEL)
    icons_row(img, 1274, scale=0.75, gap=36)
    return np.array(img.convert("RGB"))[:, :, ::-1]


def border(frame, p, th=7):
    per = 2 * (W + H)
    L = p * per
    segs = [((0, 0), (W, 0)), ((W, 0), (W, H)), ((W, H), (0, H)), ((0, H), (0, 0))]
    col = YEL[::-1]
    for (x0, y0), (x1, y1) in segs:
        seg = abs(x1 - x0) + abs(y1 - y0)
        if L <= 0:
            break
        f = min(1, L / seg)
        xe, ye = int(x0 + (x1 - x0) * f), int(y0 + (y1 - y0) * f)
        xa, xb = sorted((x0, xe)); ya, yb = sorted((y0, ye))
        if y0 == y1:
            yy = 0 if y0 == 0 else H - th
            frame[yy:yy + th, max(0, xa):min(W, xb)] = col
        else:
            xx = 0 if x0 == 0 else W - th
            frame[max(0, ya):min(H, yb), xx:xx + th] = col
        L -= seg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("headline")
    ap.add_argument("--hl", default="")
    ap.add_argument("--shift", type=int, default=0)
    a = ap.parse_args()
    info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                               "stream=width,height:format=duration", "-of", "json", a.src]))
    sw, sh = info["streams"][0]["width"], info["streams"][0]["height"]
    dur = float(info["format"]["duration"])
    vh = int(round(sh * W / sw / 2) * 2)
    ov = overlay(a.headline, [w for w in a.hl.split(",") if w])
    ova = np.array(ov).astype(np.float32)
    oa = ova[:, :, 3:4] / 255.0
    orgb = ova[:, :, :3][:, :, ::-1]
    out_frame = outro_img()
    # fade mask for the sharp video bottom edge
    top = -a.shift
    fade_px = 160
    mask = np.ones((vh, 1, 1), np.float32)
    if a.shift > 0 or vh < H:
        for i in range(fade_px):
            mask[vh - fade_px + i] = 1 - i / fade_px
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", a.src, "-vf", f"scale={W}:{vh},fps={FPS}",
                            "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    total = dur + OUTRO
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", a.src,
                            "-filter_complex", f"[1:a]apad,atrim=0:{total:.3f},afade=t=out:st={dur - FADE:.3f}:d={FADE}[a]",
                            "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", a.out],
                           stdin=subprocess.PIPE)
    n, nb = 0, W * vh * 3
    nframes = int(dur * FPS)
    while True:
        buf = dec.stdout.read(nb)
        if len(buf) < nb:
            break
        fr = np.frombuffer(buf, np.uint8).reshape(vh, W, 3)
        small = cv2.resize(fr, (W // 10, vh // 10))
        small = cv2.GaussianBlur(small, (0, 0), 3)
        bg = cv2.resize(small, (W, H)).astype(np.float32) * 0.45
        y0, y1 = max(0, top), min(H, top + vh)
        part = fr[y0 - top:y1 - top].astype(np.float32)
        m = mask[y0 - top:y1 - top]
        bg[y0:y1] = part * m + bg[y0:y1] * (1 - m)
        canvas = bg * (1 - oa) + orgb * oa
        t = n / FPS
        if t > dur - FADE:
            canvas *= max(0, (dur - t) / FADE)
        frame = canvas.clip(0, 255).astype(np.uint8)
        border(frame, min(1, n / max(1, nframes - 1)))
        enc.stdin.write(frame.tobytes())
        n += 1
    for k in range(int(OUTRO * FPS)):
        f = min(1, k / (0.4 * FPS))
        enc.stdin.write((out_frame.astype(np.float32) * f).astype(np.uint8).tobytes())
    enc.stdin.close(); enc.wait(); dec.wait()
    print("done", a.out, n, "frames")


if __name__ == "__main__":
    main()
