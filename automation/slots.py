"""RiseUp Pakistan publishing slots, RiseUp-day accounting and source policy.

ONE rule set, used by the GitHub workflow AND described word-for-word in riseup-chatgpt-prompt.txt.

Slots (Asia/Karachi, UTC+05:00, no daylight saving):
  10:00 11:00 ... 23:00 of day D, plus 00:00 of D+1  -> 15 slots that all belong to RiseUp day D.
Preparation runs at HH:45 for the slot at HH+1:00 (the 23:45 run prepares 00:00 of the NEXT calendar date).
Freshness: the story's newest qualifying timestamp must be within 2 hours BEFORE the target slot
           (and not in the future relative to the preparation time).
Verification: 2 sources on 2 different approved news outlets, OR 1 approved official primary source.
"""
import datetime as dt
from urllib.parse import urlparse

PKT = dt.timezone(dt.timedelta(hours=5))
SLOT_HOURS = (10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 0)
FRESH_MAX_H = 8.0          # owner 15 Oct: newest first (2h, 3h, 4h, 6h), max 8h
STORY_DELAY_MIN = 5          # FB/IG Story goes out 5 minutes after the feed post
MIN_LEAD_MIN = 5             # never schedule closer than 5 minutes from "now"
LATE_GRACE_MIN = 15          # a late run may publish up to slot+15 min, otherwise the slot is missed

# outlet key -> registered domains. Two sources must have two DIFFERENT outlet keys.
TRUSTED_OUTLETS = {
    "dawn": ("dawn.com",),
    "tribune": ("tribune.com.pk",),
    "geo": ("geo.tv",),
    "thenews": ("thenews.com.pk",),
    "brecorder": ("brecorder.com",),
    "app": ("app.com.pk",),
    "ptv": ("ptv.com.pk", "ptvnews.ptv.com.pk"),
    "bbc": ("bbc.com", "bbc.co.uk"),
    "reuters": ("reuters.com",),
    "ap": ("apnews.com",),
    "aljazeera": ("aljazeera.com",),
    "arabnews": ("arabnews.pk", "arabnews.com"),
}
# official primary sources: any *.gov.pk site plus these named bodies
OFFICIAL_SUFFIXES = (".gov.pk",)
OFFICIAL_DOMAINS = ("sbp.org.pk", "ispr.gov.pk", "pbs.gov.pk", "finance.gov.pk", "pmo.gov.pk",
                    "ogra.org.pk", "nepra.org.pk", "pcb.com.pk", "pta.gov.pk", "nadra.gov.pk",
                    "ecp.gov.pk", "fbr.gov.pk", "psx.com.pk", "pmd.gov.pk", "ndma.gov.pk")


def to_pkt(t):
    if t.tzinfo is None:
        raise ValueError("timestamp has no timezone offset")
    return t.astimezone(PKT)


def is_slot(t):
    t = to_pkt(t)
    return t.minute == 0 and t.second == 0 and t.hour in SLOT_HOURS


def riseup_day(t):
    """The RiseUp day a slot belongs to: 00:00 (and anything before 10:00) counts to the previous date."""
    t = to_pkt(t)
    return (t - dt.timedelta(days=1)).date() if t.hour < 10 else t.date()


def day_slots(day):
    """All 15 slots of RiseUp day `day` (a date)."""
    base = dt.datetime(day.year, day.month, day.day, tzinfo=PKT)
    return [base + dt.timedelta(hours=h if h else 24) for h in SLOT_HOURS]


def next_slot(now):
    """First slot strictly after `now` (the slot the HH:45 run prepares)."""
    now = to_pkt(now)
    t = (now + dt.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    while t.hour not in SLOT_HOURS:
        t += dt.timedelta(hours=1)
    return t


def publication_time(slot, now):
    """Exact time to send to Metricool for `slot`, or None if the slot was missed.
    On time -> the slot itself. Late (<5 min left) -> now+5 min, rounded up to the minute,
    but only while that is within slot+15 min."""
    slot, now = to_pkt(slot), to_pkt(now)
    earliest = now + dt.timedelta(minutes=MIN_LEAD_MIN)
    if slot >= earliest:
        return slot
    t = earliest.replace(second=0, microsecond=0)
    if t < earliest:
        t += dt.timedelta(minutes=1)
    return t if t <= slot + dt.timedelta(minutes=LATE_GRACE_MIN) else None


TIKTOK_SLOTS = (10, 12, 14, 16, 18, 20, 22, 0)   # 8 TikTok slots spread over the day


def tiktok_quota(slot):
    """How many TikTok posts the RiseUp day may have once `slot` is published: the number of TikTok slots
    up to and including it. A skipped TikTok slot rolls its TikTok to the next published story."""
    slot = to_pkt(slot)
    day = riseup_day(slot)
    return sum(1 for s in day_slots(day) if s <= slot and s.hour in TIKTOK_SLOTS)


def story_time(pub):
    return pub + dt.timedelta(minutes=STORY_DELAY_MIN)


def domain(url):
    h = (urlparse(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def _match(host, dom):
    return host == dom or host.endswith("." + dom)


def outlet_key(url):
    host = domain(url)
    for key, doms in TRUSTED_OUTLETS.items():
        if any(_match(host, d) for d in doms):
            return key
    return None


def is_official(url):
    host = domain(url)
    return host.endswith(OFFICIAL_SUFFIXES) or any(_match(host, d) for d in OFFICIAL_DOMAINS)


def verification(sources):
    """Return (ok, explanation). sources: list of {url,...}."""
    urls = [s.get("url", "") for s in sources if isinstance(s, dict)]
    official = [u for u in urls if is_official(u)]
    outlets = {outlet_key(u) for u in urls} - {None}
    unknown = [u for u in urls if not is_official(u) and outlet_key(u) is None]
    if unknown:
        return False, "source not on the approved list: " + ", ".join(unknown)
    if official:
        return True, "official primary source: " + domain(official[0])
    if len(outlets) >= 2:
        return True, "2 independent outlets: " + ", ".join(sorted(outlets))
    return False, "needs 2 sources from 2 DIFFERENT approved outlets, or 1 official primary source"


def effective_time(src, parse):
    """Newest qualifying time of one source: published_at, or updated_at when substantive_update is true."""
    t = parse(src["published_at"])
    if src.get("updated_at") and src.get("substantive_update") is True:
        t = max(t, parse(src["updated_at"]))
    return t


def freshness(sources, slot, now, parse):
    """Return (ok, age_hours_at_slot, message). Freshest qualifying source decides; none may be in the future."""
    times = [effective_time(s, parse) for s in sources]
    if any(t > now + dt.timedelta(minutes=10) for t in times):
        return False, None, "a source timestamp is in the future - check the time zone (+05:00 for PKT)"
    newest = max(times)
    age = (slot - newest).total_seconds() / 3600
    if age > FRESH_MAX_H:
        return False, round(age, 2), (f"stale: newest qualifying timestamp {newest:%Y-%m-%d %H:%M} PKT is "
                                      f"{age:.2f} h before the {slot:%H:%M} slot (max {FRESH_MAX_H:g} h)")
    return True, round(age, 2), ""


def card_date(t):
    """Card / caption date text, e.g. '14 OCT 2026' (renderer upper-cases anyway)."""
    return to_pkt(t).strftime("%d %b %Y").upper()
