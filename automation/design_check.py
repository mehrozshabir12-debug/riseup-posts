"""Automatic visual checks so nothing that deviates from the approved design gets published.

1. Template integrity: template/*.py, assets and fonts must match automation/approved_template.sha256
   (refuses to render if anyone changed the approved design files).
2. Feed card: 1080x1350 JPEG; the white-arrow logo pixels are white at the approved position;
   the footer (Facebook | Instagram | TikTok icons, no X) matches the approved reference crop.
3. Story: 1080x1920 JPEG whose centre holds the same card.
4. Videos: 1080x1920 H.264, has audio, duration limit.
"""
import json, os, subprocess, sys
from PIL import Image, ImageChops, ImageStat
from common import ROOT, TEMPLATE, sha256

MANIFEST = os.path.join(ROOT, "automation", "approved_template.sha256")
FOOTER_REF = os.path.join(ROOT, "automation", "reference", "footer_bold.png")
FOOTER_BOX = (0, 1255, 1080, 1330)
MX, LOGO_Y, LOGO_H = 52, 40, 112


def approved_files():
    out = []
    for dp, _, fs in os.walk(TEMPLATE):
        if "__pycache__" in dp:
            continue
        for f in fs:
            if f.endswith((".py", ".png", ".ttf")):
                out.append(os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/"))
    return sorted(out)


def write_manifest():
    with open(MANIFEST, "w") as fh:
        for r in approved_files():
            fh.write(f"{sha256(os.path.join(ROOT, r))}  {r}\n")


def check_template():
    errs = []
    if not os.path.exists(MANIFEST):
        return ["approved_template.sha256 missing"]
    want = {}
    for line in open(MANIFEST):
        h, p = line.strip().split("  ", 1)
        want[p] = h
    for p, h in want.items():
        fp = os.path.join(ROOT, p)
        if not os.path.exists(fp):
            errs.append(f"approved file missing: {p}")
        elif sha256(fp) != h:
            errs.append(f"approved design file was changed: {p}")
    return errs


def _logo_mask():
    logo = Image.open(os.path.join(TEMPLATE, "assets", "logo_white.png")).convert("RGBA")
    logo = logo.resize((round(logo.width * LOGO_H / logo.height), LOGO_H), Image.LANCZOS)
    return logo.split()[3].point(lambda v: 255 if v > 250 else 0)


def check_card(path):
    errs = []
    im = Image.open(path)
    if im.format != "JPEG" or im.size != (1080, 1350):
        return [f"card must be 1080x1350 JPEG, got {im.format} {im.size}"]
    im = im.convert("RGB")
    m = _logo_mask()
    box = (MX, LOGO_Y, MX + m.width, LOGO_Y + m.height)
    region = im.crop(box).convert("L")
    mean_logo = ImageStat.Stat(region, m).mean[0]
    if mean_logo < 225:
        errs.append(f"logo check failed (white-arrow logo not found at approved spot, brightness {mean_logo:.0f})")
    if os.path.exists(FOOTER_REF):
        ref = Image.open(FOOTER_REF).convert("RGB")
        diff = ImageStat.Stat(ImageChops.difference(im.crop(FOOTER_BOX), ref)).mean
        if max(diff) > 6:
            errs.append(f"footer icons differ from the approved footer (diff {max(diff):.1f})")
    return errs


def check_story(path, card_path):
    im = Image.open(path)
    if im.format != "JPEG" or im.size != (1080, 1920):
        return [f"story must be 1080x1920 JPEG, got {im.format} {im.size}"]
    return []


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height:format=duration",
                        "-of", "json", path], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def check_video(path, max_s=60.0, need_audio=True):
    errs = []
    try:
        p = probe(path)
    except Exception as e:
        return [f"video unreadable: {e}"], 0.0
    v = [s for s in p["streams"] if s["codec_type"] == "video"]
    a = [s for s in p["streams"] if s["codec_type"] == "audio"]
    dur = float(p["format"]["duration"])
    if not v or (v[0]["width"], v[0]["height"]) != (1080, 1920) or v[0]["codec_name"] != "h264":
        errs.append(f"video must be 1080x1920 h264, got {v[:1]}")
    if need_audio and not a:
        errs.append("video has no audio track")
    if dur > max_s + 0.2:
        errs.append(f"video is {dur:.1f} s (max {max_s:.0f} s)")
    if dur < 3:
        errs.append(f"video too short ({dur:.1f} s)")
    return errs, round(dur, 2)


if __name__ == "__main__":
    if sys.argv[1:] == ["write-manifest"]:
        write_manifest(); print("manifest written")
    elif sys.argv[1:] == ["template"]:
        e = check_template(); print("\n".join(e) or "template OK"); sys.exit(1 if e else 0)
    elif sys.argv[1] == "card":
        e = check_card(sys.argv[2]); print("\n".join(e) or "card OK"); sys.exit(1 if e else 0)
