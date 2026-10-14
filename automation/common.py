"""Shared helpers for the RiseUp Pakistan GitHub automation."""
import json, os, re, datetime as dt, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "template")
POSTS = os.path.join(ROOT, "posts")
REQUESTS = os.path.join(ROOT, "requests")
RESULTS = os.path.join(ROOT, "results")
RECEIPTS = os.path.join(ROOT, "receipts")
WORK = os.path.join(ROOT, ".work")

REPO = os.environ.get("GITHUB_REPOSITORY", "mehrozshabir12-debug/riseup-posts")
BRANCH = os.environ.get("RISEUP_BRANCH", "main")
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
BLOG_ID = os.environ.get("METRICOOL_BLOG_ID") or "7305396"
TZ_NAME = "Asia/Karachi"
PKT = dt.timezone(dt.timedelta(hours=5))

LOG_FOR_TYPE = {"news": "posted_log.json", "star": "celebrity_log.json", "tribute": "tribute_log.json"}
ALL_LOGS = ("posted_log.json", "celebrity_log.json", "tribute_log.json")

DAILY_NEWS_CAP = 15
DAILY_STAR_CAP = 3
DAILY_TIKTOK_CAP = 8
TRIBUTE_VERSIONS_CAP = 3
POST_START_H, POST_END = 10, (23, 59)
MIN_GAP_MIN = 30          # keep ~30 min between news posts
REEL_MAX_S = 60.0


def now_pkt():
    fake = os.environ.get("RISEUP_FAKE_NOW")  # tests only
    if fake:
        return dt.datetime.fromisoformat(fake).astimezone(PKT)
    return dt.datetime.now(PKT)


def parse_time(s):
    t = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=PKT)
    return t.astimezone(PKT)


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def load_log(name):
    data = load_json(os.path.join(ROOT, name), [])
    return [x for x in data if isinstance(x, dict)] if isinstance(data, list) else []


def append_log(name, entry):
    path = os.path.join(ROOT, name)
    data = load_json(path, [])
    data = data if isinstance(data, list) else []
    rid = entry.get("request_id")
    data = [x for x in data if not (isinstance(x, dict) and rid and x.get("request_id") == rid)]
    data.append(entry)
    save_json(path, data)


def update_log_entry(request_id, updater):
    for name in ALL_LOGS:
        path = os.path.join(ROOT, name)
        data = load_json(path, [])
        changed = False
        for x in data if isinstance(data, list) else []:
            if isinstance(x, dict) and x.get("request_id") == request_id:
                updater(x)
                changed = True
        if changed:
            save_json(path, data)
            return True
    return False


def entry_day(e):
    """RiseUp day of a log entry. A post scheduled at 00:00-09:59 PKT belongs to the PREVIOUS date
    (the midnight slot closes RiseUp day D), so caps such as TikTok 8/day are counted correctly."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2})", str(e.get("scheduled") or ""))
    if m:
        d = dt.date.fromisoformat(m.group(1))
        return (d - dt.timedelta(days=1)).isoformat() if int(m.group(2)) < 10 else d.isoformat()
    for k in ("scheduled", "published", "date"):
        v = str(e.get(k) or "")
        m = re.match(r"(\d{4}-\d{2}-\d{2})", v)
        if m:
            return m.group(1)
    return ""


def counts_toward_caps(e):
    return e.get("publish_status") not in ("failed", "cancelled", "rejected", "dry_run")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def raw_url(path):
    return RAW + rel(path)
