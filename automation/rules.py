"""Request validation, duplicate prevention, daily caps and posting-time rules."""
import re, sys, os, datetime as dt
from urllib.parse import urlparse
from common import (ROOT, TEMPLATE, PKT, ALL_LOGS, LOG_FOR_TYPE, DAILY_NEWS_CAP, DAILY_STAR_CAP,
                    DAILY_TIKTOK_CAP, TRIBUTE_VERSIONS_CAP, POST_START_H, POST_END, MIN_GAP_MIN,
                    load_log, entry_day, counts_toward_caps, now_pkt, parse_time)

sys.path.insert(0, TEMPLATE)
import scenes  # noqa: E402  (approved template module, only used for the scene list)

ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]{2,79}$")
NETWORKS = {"facebook", "instagram", "tiktok"}
REEL_TYPES = {"narrated", "zoom", "anime", "none"}
LANGS = {"Roman Urdu", "English"}
MOODS = {"day", "sunset", "rain", "night", "spring"}


class Reject(Exception):
    pass


def _s(x):
    return x if isinstance(x, str) else ""


def validate(req, filename):
    """Return list of errors (empty = valid)."""
    E = []
    rid = _s(req.get("id"))
    if not ID_RE.match(rid):
        E.append("id must look like 2026-10-12-short-slug (lowercase, digits, dashes)")
    stem = os.path.splitext(os.path.basename(filename))[0]
    if rid and stem != rid:
        E.append(f"file name '{stem}.json' must equal id '{rid}'")
    typ = req.get("type")
    if typ not in LOG_FOR_TYPE:
        E.append("type must be news, star or tribute")
    if len(_s(req.get("headline")).strip()) < 15:
        E.append("headline (full factual sentence, used for duplicate checks) is required")
    if req.get("language") not in LANGS:
        E.append("language must be 'Roman Urdu' or 'English'")

    srcs = req.get("sources")
    if not isinstance(srcs, list) or not srcs:
        E.append("sources: at least one {outlet, url, published_at} is required")
        srcs = []
    for i, s in enumerate(srcs):
        if not isinstance(s, dict):
            E.append(f"sources[{i}] must be an object"); continue
        if not _s(s.get("outlet")).strip():
            E.append(f"sources[{i}].outlet missing")
        u = urlparse(_s(s.get("url")))
        if u.scheme != "https" or not u.netloc:
            E.append(f"sources[{i}].url must be an https article URL")
        try:
            parse_time(s.get("published_at"))
        except Exception:
            E.append(f"sources[{i}].published_at must be ISO time, e.g. 2026-10-12T15:10:00+05:00")
    if typ == "tribute":
        doms = {urlparse(_s(s.get("url"))).netloc.lower().removeprefix("www.") for s in srcs if isinstance(s, dict)}
        if len(doms) < 2:
            E.append("tribute (death news) needs 2 independent credible sources on different websites")
    if typ in ("star", "tribute") and not _s((req.get("person") or {}).get("name")).strip():
        E.append("person.name is required for star and tribute posts")

    card = req.get("card")
    if not isinstance(card, dict):
        E.append("card object is required"); card = {}
    if card.get("scene") not in scenes.SCENES:
        E.append(f"card.scene must be one of: {', '.join(sorted(scenes.SCENES))}")
    for k, mx in (("head1", 30), ("head2_hl", 24), ("head2", 30), ("kicker", 40), ("desc", 110), ("source", 40), ("date", 20)):
        v = card.get(k, "")
        if not isinstance(v, str):
            E.append(f"card.{k} must be text")
        elif len(v) > mx:
            E.append(f"card.{k} too long ({len(v)} > {mx} characters)")
    for k in ("head1", "source", "date"):
        if not _s(card.get(k)).strip():
            E.append(f"card.{k} is required")
    if not (_s(card.get("head2")).strip() or _s(card.get("head2_hl")).strip()):
        E.append("card.head2 or card.head2_hl is required")
    if "seed" in card and not isinstance(card["seed"], int):
        E.append("card.seed must be an integer")
    if "photo" in card:
        E.append("card.photo is not allowed: only the approved original scene graphics are used")

    reel = req.get("reel") or {"type": "none"}
    if not isinstance(reel, dict) or reel.get("type") not in REEL_TYPES:
        E.append("reel.type must be narrated, zoom, anime or none")
        reel = {}
    rt = reel.get("type")
    if typ == "star" and rt not in (None, "none"):
        E.append("star posts have no Reel (reel.type must be none)")
    if rt == "narrated":
        segs = reel.get("segments")
        if not isinstance(segs, list) or not 2 <= len(segs) <= 6:
            E.append("reel.segments: 2-6 items of {text, voice}")
            segs = []
        for i, sg in enumerate(segs):
            if not isinstance(sg, dict) or not _s(sg.get("text")).strip() or not _s(sg.get("voice")).strip():
                E.append(f"reel.segments[{i}] needs text (on screen) and voice (spoken)")
            elif len(sg["text"].replace("**", "")) > 190:
                E.append(f"reel.segments[{i}].text too long (max 190 characters)")
        for k in ("intro_voice", "outro_question"):
            if not _s(reel.get(k)).strip():
                E.append(f"reel.{k} is required for a narrated Reel")
        if reel.get("scenes") is not None:
            if not isinstance(reel["scenes"], list) or any(s not in scenes.SCENES for s in reel["scenes"]):
                E.append("reel.scenes must be a list of valid scene names")
    if rt == "anime":
        p = reel.get("paragraphs")
        if not isinstance(p, list) or not 3 <= len(p) <= 6 or not all(isinstance(x, str) and x.strip() for x in p):
            E.append("reel.paragraphs: 3-6 short paragraphs are required for an anime Reel")
        if reel.get("mood") and reel["mood"] not in MOODS:
            E.append(f"reel.mood must be one of {sorted(MOODS)}")

    cap = _s(req.get("caption"))
    if len(cap.strip()) < 40:
        E.append("caption is required")
    else:
        if "#RiseUpPakistan" not in cap:
            E.append("caption hashtags must include #RiseUpPakistan")
        if "Source:" not in cap:
            E.append("caption must contain 'Source: <outlet>'")
        if "ghibli" in cap.lower():
            E.append("never mention Ghibli")
        if len(cap) > 2100:
            E.append("caption too long (max 2100 characters)")
    tt = _s(req.get("tiktok_title"))
    if len(tt) > 90:
        E.append("tiktok_title max 90 characters")

    pub = req.get("publish") or {}
    nets = pub.get("networks", ["facebook", "instagram", "tiktok"])
    if not isinstance(nets, list) or not nets or not set(nets) <= NETWORKS:
        E.append("publish.networks must be a subset of facebook, instagram, tiktok")
    at = pub.get("at", "auto")
    if at != "auto":
        try:
            parse_time(at)
        except Exception:
            E.append("publish.at must be 'auto' or an ISO time with +05:00")
    music = req.get("music")
    if music is not None and not (isinstance(music, dict) and _s(str(music.get("audioId", ""))).strip()):
        E.append("music must be {\"audioId\": \"<numeric id or exact search term>\"}")
    return E


# ---------------- duplicates / caps ----------------

def _norm_words(t):
    return {w for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) > 2}


def _entry_urls(e):
    urls = [e.get("source"), e.get("source2")]
    for s in e.get("sources") or []:
        if isinstance(s, dict):
            urls.append(s.get("url"))
    return {u.strip().rstrip("/") for u in urls if isinstance(u, str) and u.startswith("http")}


def all_entries():
    out = []
    for name in ALL_LOGS:
        for e in load_log(name):
            out.append((name, e))
    return out


def check_duplicates(req):
    """Raise Reject if this story was already posted. Tributes may have up to 3 versions per person."""
    rid, typ = req["id"], req["type"]
    urls = {s["url"].strip().rstrip("/") for s in req["sources"]}
    words = _norm_words(req["headline"])
    person = _s((req.get("person") or {}).get("name")).strip().lower()
    today = now_pkt().date()
    tribute_versions = 0
    for name, e in all_entries():
        if e.get("request_id") == rid and counts_toward_caps(e):
            raise Reject(f"request id {rid} is already in {name}")
        if not counts_toward_caps(e):
            continue
        if typ == "tribute":
            ep = _s((e.get("person") or "") if isinstance(e.get("person"), str) else (e.get("person") or {}).get("name")).lower()
            if name == "tribute_log.json" and person and (ep == person or person in _s(e.get("headline")).lower()):
                tribute_versions += 1
            continue
        if name == "tribute_log.json":
            continue
        if urls & _entry_urls(e):
            raise Reject(f"duplicate: source URL already used in {name} ({e.get('headline', '')[:80]})")
        try:
            d = dt.date.fromisoformat(entry_day(e))
        except ValueError:
            continue
        if abs((today - d).days) <= 3:
            ew = _norm_words(_s(e.get("headline")))
            if words and ew:
                j = len(words & ew) / len(words | ew)
                if j >= 0.6:
                    raise Reject(f"duplicate: same story as '{e.get('headline', '')[:80]}' ({name}, similarity {j:.2f})")
    if typ == "tribute" and tribute_versions >= TRIBUTE_VERSIONS_CAP:
        raise Reject(f"tribute for {person} already has {tribute_versions} versions (max {TRIBUTE_VERSIONS_CAP})")


def day_counts(day):
    news = star = tiktok = 0
    for name, e in all_entries():
        if entry_day(e) != day or not counts_toward_caps(e):
            continue
        if name == "posted_log.json":
            news += 1
        elif name == "celebrity_log.json":
            star += 1
        if e.get("tiktok"):
            tiktok += 1
    return {"news": news, "star": star, "tiktok": tiktok}


def last_scheduled_news():
    best = None
    for name, e in all_entries():
        if name != "posted_log.json" or not counts_toward_caps(e):
            continue
        m = re.match(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})", _s(e.get("scheduled")))
        if m:
            t = dt.datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}:00").replace(tzinfo=PKT)
            best = t if best is None or t > best else best
    return best


def in_hours(t):
    return POST_START_H <= t.hour and (t.hour, t.minute) <= POST_END


def pick_slot(req):
    """Return publish datetime (PKT). Explicit times must be inside 10:00-23:59 and >= now+5 min."""
    now = now_pkt()
    at = (req.get("publish") or {}).get("at", "auto")
    if at != "auto":
        t = parse_time(at)
        if t < now + dt.timedelta(minutes=5):
            raise Reject(f"publish.at {t:%Y-%m-%d %H:%M} PKT is in the past or less than 5 minutes away")
        if not in_hours(t):
            raise Reject("publish.at must be between 10:00 AM and 11:59 PM Pakistan time")
        return t
    t = now + dt.timedelta(minutes=20)   # time for ChatGPT to read results and schedule
    if req["type"] == "news":
        last = last_scheduled_news()
        if last and t < last + dt.timedelta(minutes=MIN_GAP_MIN):
            t = last + dt.timedelta(minutes=MIN_GAP_MIN)
    t = t.replace(second=0, microsecond=0)
    if not in_hours(t):
        nxt = t if t.hour < POST_START_H else t + dt.timedelta(days=1)
        t = nxt.replace(hour=POST_START_H, minute=5)
    return t


def check_caps(req, slot):
    """Raise Reject on cap overflow. Returns (allow_tiktok, notes)."""
    c = day_counts(slot.strftime("%Y-%m-%d"))
    if req["type"] == "news" and c["news"] >= DAILY_NEWS_CAP:
        raise Reject(f"daily cap reached: {c['news']}/{DAILY_NEWS_CAP} news on {slot:%Y-%m-%d}")
    if req["type"] == "star" and c["star"] >= DAILY_STAR_CAP:
        raise Reject(f"daily cap reached: {c['star']}/{DAILY_STAR_CAP} star posts on {slot:%Y-%m-%d}")
    notes = []
    allow_tt = c["tiktok"] < DAILY_TIKTOK_CAP
    if not allow_tt:
        notes.append(f"TikTok skipped: {c['tiktok']}/{DAILY_TIKTOK_CAP} TikTok posts already on {slot:%Y-%m-%d}")
    return allow_tt, notes, c


def freshness(req):
    """Reject news older than 24 h; warn if older than 2 h."""
    now = now_pkt()
    first = min(parse_time(s["published_at"]) for s in req["sources"])
    age_h = (now - first).total_seconds() / 3600
    notes = []
    if age_h < -0.2:
        raise Reject("source published_at is in the future - check the time zone (+05:00 for PKT)")
    limit = 24 if req["type"] != "tribute" else 48
    if age_h > limit:
        raise Reject(f"stale: source is {age_h:.1f} h old (max {limit} h; preferred under 2 h)")
    if age_h > 2:
        notes.append(f"source is {age_h:.1f} h old (owner prefers news from the last 2 hours)")
    return notes, round(age_h, 2)
