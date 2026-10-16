"""Runway API: text -> realistic news photo (no text in it). Used by process_request when card.photo_prompt is set.

Needs the GitHub secret RUNWAY_API_KEY (Runway developer portal). Never hard-code the key.
API: POST https://api.dev.runwayml.com/v1/text_to_image, then poll GET /v1/tasks/{id}.
Cost (Oct 2026): gen4_image 1080p = 8 credits (~$0.08), 720p = 5 credits.
"""
import json, os, time, urllib.request, urllib.error

BASE = "https://api.dev.runwayml.com/v1"
VERSION = "2024-11-06"
MODEL = os.environ.get("RUNWAY_MODEL") or "gen4_image"
RATIOS = [r for r in (os.environ.get("RUNWAY_RATIO"), "1440:1080", "1920:1080") if r]   # landscape, top of card
STYLE = (" Photorealistic documentary news photograph, natural light, realistic people and places, "
         "sharp focus. Absolutely no text, letters, numbers, signs, captions, logos, watermarks or frames.")


def available():
    return bool(os.environ.get("RUNWAY_API_KEY"))


def _call(method, path, body=None, timeout=60):
    req = urllib.request.Request(BASE + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + os.environ["RUNWAY_API_KEY"],
                                          "X-Runway-Version": VERSION, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode(errors="replace")[:600]}


def generate(prompt, dst, max_wait=300, poll=5):
    """Create one photo for `prompt`, save it to `dst`. Returns info dict. Raises RuntimeError with Runway's message."""
    if not available():
        raise RuntimeError("RUNWAY_API_KEY secret is not set in GitHub")
    last = None
    for ratio in RATIOS:
        status, resp = _call("POST", "/text_to_image",
                             {"model": MODEL, "promptText": (prompt.strip() + STYLE)[:1000], "ratio": ratio})
        if 200 <= status < 300 and resp.get("id"):
            break
        last = f"HTTP {status}: {resp.get('error') or resp}"
        if status != 400:                      # only a bad ratio is worth retrying with another ratio
            raise RuntimeError(f"Runway refused the request ({last})")
    else:
        raise RuntimeError(f"Runway refused the request ({last})")
    tid, t0 = resp["id"], time.time()
    while time.time() - t0 < max_wait:
        time.sleep(poll)
        status, task = _call("GET", f"/tasks/{tid}")
        st = task.get("status")
        if st == "SUCCEEDED":
            url = (task.get("output") or [None])[0]
            if not url:
                raise RuntimeError("Runway task succeeded but returned no image")
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "RiseUp"}), timeout=120) as r, \
                    open(dst, "wb") as f:
                f.write(r.read())
            return {"task_id": tid, "model": MODEL, "ratio": ratio, "seconds": round(time.time() - t0)}
        if st in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"Runway task {st}: {task.get('failure') or task.get('failureCode') or task}")
    raise RuntimeError(f"Runway task {tid} did not finish in {max_wait} s")
