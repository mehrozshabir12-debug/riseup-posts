"""Request validation, duplicate prevention, daily caps and posting-time rules."""
import re, sys, os, datetime as dt
from urllib.parse import urlparse
from common import (ROOT, TEMPLATE, PKT, ALL_LOGS, LOG_FOR_TYPE, DAILY_NEWS_CAP, DAILY_STAR_CAP,
                    DAILY_TIKTOK_CAP, TRIBUTE_VERSIONS_CAP, POST_START_H, POST_END, MIN_GAP_MIN,
                    load_log, entry_day, counts_toward_caps, now_pkt, parse_time)

sys.path.insert(0, TEMPLATE)
import scenes  # noqa: E402  (approved template module, only used for the scene list)
import slots   # noqa: E402  (slot, RiseUp-day, freshness and source rules - single source of truth)

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
        for tk in ("published_at", "updated_at"):
            if tk == "updated_at" and not s.get(tk):
                continue
            v = _s(s.get(tk))
            if not re.search(r"(Z|[+-]\d{2}:\d{2})$", v):
                E.append(f"sources[{i}].{tk} must be an ISO time WITH offset, e.g. 2026-10-12T15:10:00+05:00")
                continue
            try:
                parse_time(v)
            except Exception:
                E.append(f"sources[{i}].{tk} must be ISO time, e.g. 2026-10-12T15:10:00+05:00")
        if s.get("updated_at") and not isinstance(s.get("substantive_update"), bool):
            E.append(f"sources[{i}].substantive_update must be true or false when updated_at is given")
    if srcs and all(isinstance(s, dict) and s.get("url") for s in srcs):
        ok, why = slots.verification(srcs)
        if not ok:
            E.append("verification: " + why)
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
    try:
        primary = min(srcs, key=lambda x: parse_time(x["published_at"]))
        want = slots.card_date(parse_time(primary["published_at"]))
    except Exception:
        want = None                       # source time errors are reported above
    if want and _s(card.get("date")).strip().upper() != want:
        E.append(f"card.date must be the source publication date '{want}' (earliest source, PKT), "
                 f"not '{card.get('date')}'")
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
            elif sg["text"].count("**") % 2:
                E.append(f"reel.segments[{i}].text has an unclosed ** highlight")
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
        tags = re.findall(r"#\w+", cap)
        if "#RiseUpPakistan" not in tags:
            E.append("caption hashtags must include #RiseUpPakistan")
        if len(tags) != 5:
            E.append(f"caption must end with exactly 5 hashtags (found {len(tags)})")
        outlet = _s(card.get("source")).split("(")[0].strip().lower() if isinstance(card, dict) else ""
        if outlet and outlet not in cap.lower():
            E.append(f"caption must name the source outlet '{card.get('source')}'")
        if re.search(r"https?://", cap):
            E.append("caption must not contain links")
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
    sl = _s(pub.get("slot"))
    try:
        if not slots.is_slot(dt.datetime.fromisoformat(sl)):
            raise ValueError
    except Exception:
        E.append("publish.slot is required: the target slot, e.g. 2026-10-14T15:00:00+05:00 "
                 "(minute 00, hours 10-23 or 00 PKT)")
    if "dry_run" in pub and not isinstance(pub["dry_run"], bool):
        E.append("publish.dry_run must be true or false")
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
    """Posting hours for retries: 10:00-23:59 PKT plus 00:00-00:30 (the midnight slot and its Story)."""
    t = t.astimezone(PKT)
    return t.hour >= 10 or (t.hour == 0 and t.minute <= 30)


def pick_slot(req):
    """Return (slot, publication_time) in PKT, or raise Reject.
    The request names its target slot; publication is the slot itself, or now+5 min for a late run
    (only up to slot+15 min). A slot already used by another live story is refused."""
    now = now_pkt()
    slot = parse_time(req["publish"]["slot"])
    pub = slots.publication_time(slot, now)
    if pub is None:
        raise Reject(f"slot {slot:%Y-%m-%d %H:%M} PKT was missed (now {now:%H:%M}); never schedule in the past")
    for name, e in all_entries():
        if counts_toward_caps(e) and _s(e.get("slot")) == slot.isoformat():
            raise Reject(f"slot {slot:%H:%M} PKT already has a story: {e.get('headline', '')[:80]}")
    return slot, pub


def check_caps(req, slot):
    """Raise Reject on cap overflow. Returns (allow_tiktok, notes)."""
    day = slots.riseup_day(slot).isoformat()
    c = day_counts(day)
    if req["type"] == "news" and c["news"] >= DAILY_NEWS_CAP:
        raise Reject(f"daily cap reached: {c['news']}/{DAILY_NEWS_CAP} news on RiseUp day {day}")
    if req["type"] == "star" and c["star"] >= DAILY_STAR_CAP:
        raise Reject(f"daily cap reached: {c['star']}/{DAILY_STAR_CAP} star posts on RiseUp day {day}")
    notes = []
    quota = slots.tiktok_quota(slot)
    allow_tt = c["tiktok"] < min(DAILY_TIKTOK_CAP, quota)
    if not allow_tt:
        notes.append(f"TikTok skipped: {c['tiktok']} TikTok posts on RiseUp day {day}; "
                     f"allowed by {slot:%H:%M} = {min(DAILY_TIKTOK_CAP, quota)} (max {DAILY_TIKTOK_CAP}/day)")
    return allow_tt, notes, c


def freshness(req, slot):
    """HARD rule: newest qualifying source time within 2 h before the target slot. No warnings tier."""
    ok, age_h, msg = slots.freshness(req["sources"], slot, now_pkt(), parse_time)
    if not ok:
        raise Reject(msg)
    return [], age_h
