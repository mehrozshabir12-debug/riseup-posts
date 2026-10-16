"""RiseUp Pakistan request processor (run by .github/workflows/main.yml).

  python3 automation/process_request.py render     # requests/*.json -> validate, dedupe, caps, render, checks
  python3 automation/process_request.py finalize   # verify raw URLs live, payloads, logs, optional API publish
  python3 automation/process_request.py receipts   # merge receipts/*.json (posting results from ChatGPT)
  python3 automation/process_request.py verify     # (API mode only) poll Metricool status + safe retry

Every request ends with results/<id>.json. Status values:
  rejected          validation / duplicate / cap / freshness problem (nothing rendered, nothing posted)
  failed            rendering or design check failed (nothing posted)
  awaiting_publish  media live on GitHub, payloads ready for ChatGPT's Metricool connector
  scheduled         posts created in Metricool, not yet confirmed published
  published         every network confirmed PUBLISHED
  partial           some networks published, some failed (see retry)
  publish_failed    Metricool refused the posts
"""
import glob, json, os, random, re, shutil, subprocess, sys, time, urllib.request, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import (ROOT, TEMPLATE, POSTS, REQUESTS, RESULTS, RECEIPTS, WORK, LOG_FOR_TYPE, BLOG_ID,
                    load_json, save_json, append_log, update_log_entry, now_pkt, rel, raw_url, sha256)
import rules, design_check, payloads, metricool_api

PY = sys.executable


def result_path(rid):
    return os.path.join(RESULTS, f"{rid}.json")


def write_result(rid, data):
    data["updated_at"] = now_pkt().isoformat(timespec="seconds")
    save_json(result_path(rid), data)


def run(cmd, timeout=900):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"{os.path.basename(cmd[1])} failed: {(r.stderr or r.stdout)[-600:]}")
    return r.stdout


def pending_requests():
    out = []
    for p in sorted(glob.glob(os.path.join(REQUESTS, "*.json"))):
        stem = os.path.splitext(os.path.basename(p))[0]
        try:
            req = load_json(p)
        except Exception as e:
            out.append((p, stem, None, f"invalid JSON: {e}"))
            continue
        rid = req.get("id") if isinstance(req, dict) else None
        if load_json(result_path(rid or stem)) or load_json(result_path(stem)):
            continue                     # already handled -> idempotent (a fix needs a NEW id)
        if os.path.exists(os.path.join(WORK, f"{rid or stem}.state.json")):
            continue                     # rendered in this run, waiting for finalize
        out.append((p, rid or stem, req, None))
    return out


# ---------------- render phase ----------------

def fetch_photo(url, dst, tries=6, wait=10):
    """Download the AI photo ChatGPT uploaded to Metricool; must be a real image of usable size."""
    from PIL import Image
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RiseUp-Media-Manager"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read(25 * 1024 * 1024 + 1)
            if len(data) > 25 * 1024 * 1024:
                raise ValueError("photo larger than 25 MB")
            tmp = dst + ".dl"
            with open(tmp, "wb") as f:
                f.write(data)
            im = Image.open(tmp); im.load()
            if min(im.size) < 600:
                raise ValueError(f"photo too small {im.size}")
            im.convert("RGB").save(dst, quality=95)
            os.remove(tmp)
            return dst
        except Exception as e:
            last = e
            time.sleep(wait)
    raise RuntimeError(f"download failed: {last}")

def render_one(path, rid, req):
    warnings, render_info = [], {}
    errs = rules.validate(req, path)
    if errs:
        return {"status": "rejected", "errors": errs}
    if req.get("type") == "test":
        import slots as _sl
        target = slot = _sl.next_slot(now_pkt() + dt.timedelta(minutes=5))
        req.setdefault("publish", {})["dry_run"] = True
        req.setdefault("caption", "TEST ONLY"); req.setdefault("sources", [{"outlet": "test", "url": "", "published_at": ""}])
        req.setdefault("headline", "pipeline test"); req.setdefault("language", "English")
        fresh_notes, age_h, allow_tt, cap_notes, counts = [], 0, False, ["TEST request: never published"], {}
    else:
      try:
        target, slot = rules.pick_slot(req)            # target slot (HH:00) and actual publication time
        fresh_notes, age_h = rules.freshness(req, target)
        rules.check_duplicates(req)
        allow_tt, cap_notes, counts = rules.check_caps(req, target)
      except rules.Reject as e:
        return {"status": "rejected", "errors": [str(e)]}
    warnings += fresh_notes + cap_notes

    work = os.path.join(WORK, rid)
    shutil.rmtree(work, ignore_errors=True); os.makedirs(work)
    card = dict(req["card"]); card["style"] = "bold"
    card.pop("photo", None)
    if card.get("photo_prompt"):
        import runway
        try:
            raw = os.path.join(work, f"{rid}-photo.raw")
            render_info["photo"] = runway.generate(card.pop("photo_prompt"), raw)
            from PIL import Image
            Image.open(raw).convert("RGB").save(os.path.join(work, f"{rid}-photo.jpg"), quality=95)
            os.remove(raw)
            card["photo"] = os.path.join(work, f"{rid}-photo.jpg")
        except Exception as e:
            return {"status": "failed", "errors": [f"Runway photo failed: {e}"]}
    elif card.get("photo_url"):
        try:
            card["photo"] = fetch_photo(card.pop("photo_url"), os.path.join(work, f"{rid}-photo.jpg"))
        except Exception as e:
            return {"status": "failed", "errors": [f"AI photo could not be used: {e}"]}
    if not card.get("seed"):
        card["seed"] = random.randrange(10 ** 9)
    card_cfg = os.path.join(work, f"{rid}.json"); save_json(card_cfg, card)
    feed = os.path.join(work, f"{rid}.jpg"); story = os.path.join(work, f"{rid}-story.jpg")
    for dst in (os.path.join(POSTS, f"{rid}.jpg"), os.path.join(POSTS, f"{rid}-story.jpg")):
        if os.path.exists(dst):
            return {"status": "failed", "errors": [f"{rel(dst)} already exists - approved media is never overwritten; use a new id"]}
    try:
        outp = run([PY, os.path.join(TEMPLATE, "make_post.py"), card_cfg, feed])
        for line in outp.splitlines():
            if line.startswith("WARNING"):
                warnings.append(line)
        run([PY, os.path.join(TEMPLATE, "make_story.py"), feed, story])
        errs = design_check.check_card(feed) + design_check.check_story(story, feed)
        if errs:
            return {"status": "failed", "errors": errs}
        reel_kind = (req.get("reel") or {}).get("type", "none")
        if req["type"] == "star":
            reel_kind = "none"
        reel = None
        if reel_kind == "narrated":
            reel = os.path.join(work, f"{rid}-reel.mp4")
            import news_reel
            try:
                info = news_reel.build(req, story, reel, seed=card["seed"],
                                       allow_fallback_voice=bool(req["reel"].get("allow_fallback_voice")))
                render_info["reel"] = info
                if "fallback" in str(info.get("narration_engine")):
                    warnings.append("narration used the offline fallback voice (robotic)")
            except Exception as e:
                warnings.append(f"narrated Reel failed ({e}); approved zoom Reel used instead")
                reel_kind = "zoom"
        if reel_kind == "anime":
            reel = os.path.join(work, f"{rid}-anime.mp4")
            acfg = dict(req["reel"]); acfg.pop("type", None)
            acfg.setdefault("line1", req["card"]["head1"])
            acfg.setdefault("line2", (req["card"].get("head2_hl", "") + " " + req["card"].get("head2", "")).strip())
            acfg.setdefault("sub", req["card"].get("desc", "")); acfg.setdefault("tag", req["card"].get("kicker", ""))
            acfg.setdefault("question", "Aap ka kya khayal hai?"); acfg.setdefault("source", req["card"]["source"])
            if req["type"] == "tribute":
                acfg["sad"] = True
            from news_reel import fix_highlights
            acfg["paragraphs"] = [fix_highlights(x) for x in acfg.get("paragraphs", [])]
            ap = os.path.join(work, f"{rid}-anime.json"); save_json(ap, acfg)
            o = run([PY, os.path.join(TEMPLATE, "make_anime_reel.py"), ap, reel], timeout=1500)
            m = re.search(r"mood=(\w+) seed=(\d+)", o)
            render_info["reel"] = {"mood": m.group(1), "seed": int(m.group(2))} if m else {}
        if reel_kind == "zoom":
            reel = os.path.join(work, f"{rid}.mp4")
            run([PY, os.path.join(TEMPLATE, "make_video.py"), feed, reel])
            render_info["reel"] = {"type": "zoom", "duration": 8}
        if reel:
            verrs, dur = design_check.check_video(reel, need_audio=True)
            if verrs:
                return {"status": "failed", "errors": verrs}
            render_info.setdefault("reel", {})["duration"] = dur
    except Exception as e:
        return {"status": "failed", "errors": [f"rendering failed: {e}"]}

    # all checks passed -> move into posts/
    media = {}
    for src in sorted(os.listdir(work)):
        dst = os.path.join(POSTS, src)
        shutil.move(os.path.join(work, src), dst)
    media["feed"] = rel(os.path.join(POSTS, f"{rid}.jpg"))
    media["story"] = rel(os.path.join(POSTS, f"{rid}-story.jpg"))
    if reel:
        media["reel"] = rel(os.path.join(POSTS, os.path.basename(reel)))
    media["reel_kind"] = reel_kind if reel else "none"
    shutil.rmtree(work, ignore_errors=True)
    state = {"id": rid, "revision": req.get("revision", 1), "slot": slot.isoformat(), "target_slot": target.isoformat(),
             "riseup_day": rules.slots.riseup_day(target).isoformat(), "allow_tiktok": allow_tt,
             "media": media, "card_seed": card["seed"], "render": render_info, "warnings": warnings,
             "age_hours": age_h, "counts_before": counts}
    save_json(os.path.join(WORK, f"{rid}.state.json"), state)
    return {"status": "rendered", "state": state}


def phase_render():
    ok = True
    if not os.path.isdir(REQUESTS):
        print("no requests/ folder"); return True
    todo = pending_requests()
    if not todo:
        print("no new requests"); return True
    terr = design_check.check_template()
    for path, rid, req, perr in todo:
        print(f"== {rid}")
        rev = req.get("revision", 1) if isinstance(req, dict) else 1
        if perr or not isinstance(req, dict):
            r = {"status": "rejected", "errors": [perr or "request must be a JSON object"]}
        elif terr:
            r = {"status": "failed", "errors": ["approved template integrity check failed: " + "; ".join(terr)]}
        else:
            r = render_one(path, rid, req)
        if r["status"] != "rendered":
            ok = False
            write_result(rid, {"id": rid, "revision": rev, "request": rel(path), "status": r["status"],
                               "errors": r["errors"], "warnings": [], "published": False})
        print(" ->", r["status"], r.get("errors", ""))
    return ok


# ---------------- finalize phase ----------------

def url_live(url, tries=20, wait=10):
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(wait)
    return False


def phase_finalize():
    ok = True
    for sp in sorted(glob.glob(os.path.join(WORK, "*.state.json"))):
        st = load_json(sp); rid = st["id"]
        req = load_json(os.path.join(REQUESTS, f"{rid}.json"))
        if req.get("type") == "test":                 # same defaults as in render_one; never published
            req.setdefault("publish", {})["dry_run"] = True
            req.setdefault("caption", "TEST ONLY"); req.setdefault("headline", "pipeline test")
            req.setdefault("language", "English")
            req.setdefault("sources", [{"outlet": "test", "url": "", "published_at": ""}])
        urls = {k: raw_url(os.path.join(ROOT, v)) for k, v in st["media"].items() if k != "reel_kind"}
        dead = [u for u in urls.values() if not url_live(u)]
        res = {"id": rid, "revision": st["revision"], "request": f"requests/{rid}.json", "type": req["type"],
               "headline": req["headline"], "warnings": st["warnings"], "errors": [],
               "slot_pkt": st["slot"], "target_slot": st.get("target_slot", st["slot"]),
               "riseup_day": st.get("riseup_day"), "media": urls, "media_paths": st["media"], "render": st["render"],
               "card_seed": st["card_seed"], "published": False}
        if dead:
            res.update(status="failed", errors=[f"media URL not reachable: {u}" for u in dead])
            write_result(rid, res); os.remove(sp); ok = False; continue
        slot = dt.datetime.fromisoformat(st["slot"])
        media = dict(urls); media["reel_kind"] = st["media"]["reel_kind"]
        posts, uses_tt = payloads.build(req, media, slot, st["allow_tiktok"])
        res["metricool"] = {"blogId": BLOG_ID, "mode": "api" if metricool_api.available() else "chatgpt_connector",
                            "payloads": posts, "posts": {}}
        src = req["sources"][0]
        entry = {"date": st.get("riseup_day") or slot.strftime("%Y-%m-%d"), "slot": st.get("target_slot"), "request_id": rid, "layout": "bold", "headline": req["headline"],
                 "source_outlet": src["outlet"], "source": src["url"], "sources": req["sources"],
                 "published": src["published_at"], "language": req["language"], "scene": req["card"].get("scene") or "ai_photo",
                 "seed": st["card_seed"], "image": st["media"]["feed"], "story": st["media"]["story"],
                 "tiktok": uses_tt, "anime": st["media"]["reel_kind"] == "anime",
                 "reel_kind": st["media"]["reel_kind"], "scheduled": slot.strftime("%Y-%m-%d %H:%M PKT"),
                 "music": (req.get("music") or {}).get("label") or (req.get("music") or {}).get("audioId"),
                 "publish_status": "awaiting_publish", "metricool_ids": {}}
        if "reel" in st["media"]:
            entry["video"] = st["media"]["reel"]
        if st["media"]["reel_kind"] == "anime":
            entry.update(anime_video=st["media"]["reel"], mood=st["render"].get("reel", {}).get("mood"),
                         anime_seed=st["render"].get("reel", {}).get("seed"))
        if req.get("person"):
            entry["person"] = req["person"]
        res["status"] = "awaiting_publish"
        if (req.get("publish") or {}).get("dry_run") is True:
            # test mode: real render + real payloads, but nobody publishes and nothing counts toward caps
            res["status"] = "dry_run_ready"; res["metricool"]["mode"] = "dry_run"
            entry["publish_status"] = "dry_run"
            if req["type"] != "test":
                append_log(LOG_FOR_TYPE[req["type"]], entry); res["log"] = LOG_FOR_TYPE[req["type"]]
            write_result(rid, res); os.remove(sp); print(f"== {rid} -> dry_run_ready"); continue
        if metricool_api.available():
            all_ok = True
            clash = slot_taken_in_metricool(slot)
            if clash:
                res.update(status="publish_failed", errors=[f"Metricool already has a post at {slot:%H:%M} PKT "
                                                           f"(id {clash}); not scheduling a second story in one slot"])
                entry["publish_status"] = "publish_failed"
                append_log(LOG_FOR_TYPE[req["type"]], entry); write_result(rid, res); os.remove(sp); ok = False
                continue
            for name, info in posts.items():
                r = metricool_api.create(info)
                res["metricool"]["posts"][name] = {"metricool_id": r["id"], "http": r["http"], "error": r["error"],
                                                   "status": {p["network"]: ("SCHEDULED" if r["ok"] else "ERROR") for p in info["providers"]},
                                                   "attempts": 1}
                if r["ok"]:
                    entry["metricool_ids"][name] = r["id"]
                all_ok &= r["ok"]
            res["status"] = "scheduled" if all_ok else ("partial" if entry["metricool_ids"] else "publish_failed")
            entry["publish_status"] = res["status"]
            ok &= all_ok
        append_log(LOG_FOR_TYPE[req["type"]], entry)
        res["log"] = LOG_FOR_TYPE[req["type"]]
        write_result(rid, res)
        os.remove(sp)
        print(f"== {rid} -> {res['status']}")
    return ok


def slot_taken_in_metricool(slot):
    """Id of an existing non-Story Metricool post (incl. drafts, e.g. Claude's) at this exact time, else None."""
    try:
        day = slot.strftime("%Y-%m-%d")
        for x in metricool_api.list_posts(f"{day}T00:00:00", f"{day}T23:59:59"):
            when = (x.get("publicationDate") or {}).get("dateTime", "")
            nets = [p.get("network") for p in x.get("providers", [])]
            types = [(x.get(n + "Data") or {}).get("type") for n in nets]
            story = bool(nets) and all(t == "STORY" for t in types)
            holder = str(x.get("text") or "").startswith(rules.HOLDER_MARK)
            if when[:16] == slot.strftime("%Y-%m-%dT%H:%M") and not story and not holder:
                return x.get("id")
    except Exception as e:
        print("WARNING slot check against Metricool failed:", e)
    return None


# ---------------- receipts (results reported back by ChatGPT) ----------------

def overall(posts):
    sts = [s for p in posts.values() for s in (p.get("status") or {}).values()]
    if not sts:
        return "awaiting_publish"
    if all(s == "PUBLISHED" for s in sts):
        return "published"
    if any(s == "ERROR" for s in sts):
        return "partial" if any(s == "PUBLISHED" for s in sts) else "publish_failed"
    return "scheduled"


def phase_receipts():
    for p in sorted(glob.glob(os.path.join(RECEIPTS, "*.json"))):
        rec = load_json(p); rid = rec.get("id") or os.path.splitext(os.path.basename(p))[0]
        res = load_json(result_path(rid))
        h = sha256(p)
        if not res or res.get("receipt_sha") == h:
            continue
        if rec.get("cancel"):
            if res.get("status") in ("published", "partial", "scheduled"):
                res.setdefault("warnings", []).append("cancel ignored: already sent to Metricool")
            else:
                res["status"] = "cancelled"; res["published"] = False
                res["cancel_reason"] = rec.get("reason", "")
                update_log_entry(rid, lambda e: e.update(publish_status="cancelled", cancel_reason=rec.get("reason", "")))
            res["receipt_sha"] = h
            write_result(rid, res); print(f"receipt {rid} -> {res['status']}"); continue
        if res.get("status") in ("rejected", "failed"):
            res.setdefault("warnings", []).append("receipt ignored: request was not rendered"); res["receipt_sha"] = h
            write_result(rid, res); continue
        posts = res.setdefault("metricool", {}).setdefault("posts", {})
        for name, info in (rec.get("posts") or {}).items():
            cur = posts.setdefault(name, {"attempts": 0})
            if info.get("metricool_id"):
                cur["metricool_id"] = info["metricool_id"]
            cur["status"] = {k: str(v).upper() for k, v in (info.get("status") or {}).items()}
            cur["public_urls"] = info.get("public_urls", cur.get("public_urls", {}))
            cur["attempts"] = max(cur.get("attempts", 0), int(info.get("attempts", 1)))
            if info.get("error"):
                cur["error"] = info["error"]
        res["status"] = overall(posts)
        res["published"] = res["status"] == "published"
        res["receipt_sha"] = h
        write_result(rid, res)

        def upd(e):
            e["publish_status"] = res["status"]
            e["metricool_ids"] = {k: v.get("metricool_id") for k, v in posts.items() if v.get("metricool_id")}
            e["network_status"] = {k: v.get("status") for k, v in posts.items()}
            urls = {k: v.get("public_urls") for k, v in posts.items() if v.get("public_urls")}
            if urls:
                e["public_urls"] = urls
            if rec.get("scheduled"):
                e["scheduled"] = rec["scheduled"]
        update_log_entry(rid, upd)
        print(f"receipt {rid} -> {res['status']}")
    return True


# ---------------- verify (API mode only) ----------------

def phase_verify():
    if not metricool_api.available():
        print("Metricool API secrets not set - status checks are done by ChatGPT via receipts"); return True
    now = now_pkt()
    for rp in sorted(glob.glob(os.path.join(RESULTS, "*.json"))):
        res = load_json(rp)
        if res.get("status") not in ("scheduled", "partial") or res.get("metricool", {}).get("mode") != "api":
            continue
        slot = dt.datetime.fromisoformat(res["slot_pkt"])
        if now < slot + dt.timedelta(minutes=5):
            continue
        day = slot.strftime("%Y-%m-%d")
        listed = {str(x.get("id")): x for x in metricool_api.list_posts(f"{day}T00:00:00", f"{day}T23:59:59")}
        posts = res["metricool"]["posts"]
        for name, p in posts.items():
            x = listed.get(str(p.get("metricool_id")))
            if x:
                p["status"] = {pr["network"]: pr.get("status", "UNKNOWN") for pr in x.get("providers", [])}
                p["public_urls"] = {pr["network"]: pr.get("publicUrl") for pr in x.get("providers", []) if pr.get("publicUrl")}
            failed = [n for n, s in (p.get("status") or {}).items() if s == "ERROR"]
            if failed and p.get("attempts", 1) < 3 and rules.in_hours(now + dt.timedelta(minutes=5)):
                info = dict(res["metricool"]["payloads"][name])
                info["providers"] = [{"network": n} for n in failed]   # retry ONLY the failed networks
                for k in ("facebookData", "instagramData", "tiktokData"):
                    if k[:-4] not in failed:
                        info.pop(k, None)                              # networkData only for retried networks
                info["publicationDate"] = {"dateTime": (now + dt.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:00"),
                                           "timezone": "Asia/Karachi"}
                r = metricool_api.create(info)
                p["attempts"] = p.get("attempts", 1) + 1
                p.setdefault("retries", []).append({"networks": failed, "metricool_id": r["id"], "ok": r["ok"]})
                if r["ok"]:
                    for n in failed:
                        p["status"][n] = "RETRY_SCHEDULED"
        res["status"] = overall(posts); res["published"] = res["status"] == "published"
        write_result(res["id"], res)
        update_log_entry(res["id"], lambda e: e.update(publish_status=res["status"],
                                                        network_status={k: v.get("status") for k, v in posts.items()}))
    return True


# ---------------- helpers for the workflow ----------------

def phase_needs_video():
    """Exit 0 when a pending request needs ffmpeg/TTS (a Reel), else exit 1 -> saves ~2 min per run."""
    for _, _, req, _ in pending_requests():
        if isinstance(req, dict) and (req.get("reel") or {}).get("type", "none") != "none":
            print("video needed"); return True
    print("no video needed"); return False


def phase_watchdog():
    """Fails (=> GitHub e-mails the owner) when the ChatGPT run for the upcoming slot left no run log.
    Every ChatGPT run must commit runs/<slot>.json, even when it skips the slot."""
    import slots
    now = now_pkt()
    target = slots.next_slot(now - dt.timedelta(minutes=15))   # tolerant of GitHub's late cron starts
    path = os.path.join(ROOT, "runs", target.strftime("%Y-%m-%dT%H%M") + ".json")
    if os.path.exists(path):
        log = load_json(path, {})
        print(f"watchdog: {rel(path)} -> {log.get('outcome')}")
        if str(log.get("outcome", "")).startswith("error") or log.get("outcome") == "started":
            print("::error::ChatGPT run reported an error:", log.get("errors")); return False
        return True
    print(f"::error::No ChatGPT run log for slot {target:%Y-%m-%d %H:%M} PKT ({rel(path)} missing). "
          "The automation did not run, or stopped before writing its log.")
    return False


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "render"
    ok = {"render": phase_render, "finalize": phase_finalize, "receipts": phase_receipts, "verify": phase_verify,
          "needs_video": phase_needs_video, "watchdog": phase_watchdog}[phase]()
    sys.exit(0 if ok else 3)
