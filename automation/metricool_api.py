"""Optional direct Metricool REST publishing from GitHub Actions.

Used ONLY when the repository has these GitHub Secrets (never hard-coded):
  METRICOOL_USER_TOKEN   (Metricool > Account settings > API; needs a plan with API access)
  METRICOOL_USER_ID      (numeric user id)
  METRICOOL_BLOG_ID      (optional, default 7305396)
Endpoint (Metricool docs): POST https://app.metricool.com/api/v2/scheduler/posts?blogId=..&userId=..
Header: X-Mc-Auth: <token>. Without the secrets this module does nothing and the workflow leaves
the ready payloads in results/<id>.json for ChatGPT's Metricool connector.
"""
import json, os, urllib.request, urllib.parse, urllib.error

BASE = "https://app.metricool.com/api"


def available():
    return bool(os.environ.get("METRICOOL_USER_TOKEN") and os.environ.get("METRICOOL_USER_ID"))


def _call(method, path, params=None, body=None):
    q = {"blogId": os.environ.get("METRICOOL_BLOG_ID") or "7305396", "userId": os.environ["METRICOOL_USER_ID"]}
    q.update(params or {})
    url = f"{BASE}{path}?{urllib.parse.urlencode(q)}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "X-Mc-Auth": os.environ["METRICOOL_USER_TOKEN"], "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            txt = r.read().decode() or "{}"
            return r.status, json.loads(txt)
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode(errors="replace")[:800]}


def create(info):
    body = dict(info); body["saveExternalMediaFiles"] = True
    status, resp = _call("POST", "/v2/scheduler/posts", body=body)
    data = resp.get("data") if isinstance(resp, dict) and isinstance(resp.get("data"), dict) else resp
    pid = data.get("id") if isinstance(data, dict) else None
    return {"http": status, "id": pid, "ok": 200 <= status < 300 and pid is not None,
            "error": None if 200 <= status < 300 else resp.get("error") if isinstance(resp, dict) else str(resp)}


def list_posts(start, end, tz="Asia/Karachi"):
    status, resp = _call("GET", "/v2/scheduler/posts", params={"start": start, "end": end, "timezone": tz})
    if not 200 <= status < 300:
        raise RuntimeError(f"Metricool list failed HTTP {status}: {resp}")
    return resp.get("data", resp) if isinstance(resp, dict) else resp
