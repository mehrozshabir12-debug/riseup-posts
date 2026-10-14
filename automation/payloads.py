"""Metricool post bodies, keeping the original Claude publishing settings.

Each value is the `info` object for the Metricool connector tool createScheduledPost
(blogId 7305396) and is also the JSON body for the REST API POST /api/v2/scheduler/posts.

Original settings preserved (see examples in the handover):
  normal story : FB+TikTok photo (autoAddMusic true) | IG REEL zoom MP4 + trending audio, videoVolume 0 | FB+IG Story
  anime story  : FB photo | FB REEL + IG REEL + TikTok anime MP4 (IG audio 100/35, TikTok autoAddMusic false) | Story
  star post    : FB+IG photo (+TikTok if under 8/day) | FB+IG Story, no Reel
  narrated Reel: FB photo | FB REEL + IG REEL + TikTok narrated MP4 (narration is the audio) | Story
All: autoPublish true, Reel cover (videoThumbnailUrl) = the approved card story image, Stories without text.
"""
import datetime as dt
from common import TZ_NAME

STORY_DELAY = dt.timedelta(minutes=5)   # FB/IG Story is a separate post, 5 minutes after the feed post


def _date(slot):
    return {"dateTime": slot.strftime("%Y-%m-%dT%H:%M:%S"), "timezone": TZ_NAME}


def _base(slot, text, nets, media):
    return {"publicationDate": _date(slot), "text": text, "providers": [{"network": n} for n in nets],
            "media": media, "autoPublish": True, "draft": False, "shortener": False,
            "firstCommentText": "", "mediaAltText": [], "descendants": [], "hasNotReadNotes": False,
            "smartLinkData": {"ids": []}}


def build(req, media, slot, allow_tiktok):
    """media: dict with feed, story and optionally reel (public URLs), reel_kind."""
    want = set((req.get("publish") or {}).get("networks", ["facebook", "instagram", "tiktok"]))
    tt_ok = allow_tiktok and "tiktok" in want
    typ = req["type"]
    kind = media.get("reel_kind", "none")
    cap = req["caption"]
    title = req.get("tiktok_title") or req["card"]["head1"]
    ai = req.get("ai_generated")
    if ai is None:
        ai = kind == "narrated"          # synthetic (TTS) voice -> honest AI label
    music = req.get("music") or {}
    out = {}

    def fb(t): return {"type": t}
    def ig(t, **kw):
        d = {"type": t, "isAiGenerated": bool(ai) if t in ("REEL", "POST") else False}
        if t == "REEL":
            d["showReelOnFeed"] = True
        d.update(kw); return d
    def tt(video):
        d = {"privacyOption": "PUBLIC_TO_EVERYONE", "title": title[:90], "autoAddMusic": not video,
             "disableComment": False, "disableDuet": False, "disableStitch": False}
        if video:
            d["isAigc"] = bool(ai)          # Metricool: isAigc is NOT supported on TikTok photo posts
        return d

    if typ == "star" or kind == "none":
        nets = [n for n in ("facebook", "instagram") if n in want] + (["tiktok"] if tt_ok else [])
        p = _base(slot, cap, nets, [media["feed"]])
        if "facebook" in nets: p["facebookData"] = fb("POST")
        if "instagram" in nets: p["instagramData"] = ig("POST")
        if "tiktok" in nets: p["tiktokData"] = tt(False)
        out["feed"] = p
    elif kind == "zoom":
        nets = (["facebook"] if "facebook" in want else []) + (["tiktok"] if tt_ok else [])
        if nets:
            p = _base(slot, cap, nets, [media["feed"]])
            if "facebook" in nets: p["facebookData"] = fb("POST")
            if "tiktok" in nets: p["tiktokData"] = tt(False)
            out["feed"] = p
        if "instagram" in want:
            kw = {}
            if music.get("audioId"):
                kw["audioConfiguration"] = {"audioId": str(music["audioId"]), "audioVolume": 100, "videoVolume": 0}
            p = _base(slot, cap, ["instagram"], [media["reel"]])
            p["videoThumbnailUrl"] = media["story"]
            p["instagramData"] = ig("REEL", **kw)
            out["reel"] = p
    else:  # anime or narrated: FB photo + one Reel everywhere
        if "facebook" in want:
            p = _base(slot, cap, ["facebook"], [media["feed"]]); p["facebookData"] = fb("POST")
            out["feed"] = p
        nets = [n for n in ("facebook", "instagram") if n in want] + (["tiktok"] if tt_ok else [])
        if nets:
            p = _base(slot, cap, nets, [media["reel"]])
            p["videoThumbnailUrl"] = media["story"]
            if "facebook" in nets: p["facebookData"] = fb("REEL")
            if "instagram" in nets:
                kw = {}
                if music.get("audioId"):
                    vol = (100, 35) if kind == "anime" else (12, 100)   # narration must stay clear
                    kw["audioConfiguration"] = {"audioId": str(music["audioId"]), "audioVolume": vol[0], "videoVolume": vol[1]}
                p["instagramData"] = ig("REEL", **kw)
            if "tiktok" in nets: p["tiktokData"] = tt(True)
            out["reel"] = p

    if (req.get("publish") or {}).get("stories", True):
        nets = [n for n in ("facebook", "instagram") if n in want]
        if nets:
            p = _base(slot + STORY_DELAY, "", nets, [media["story"]])
            p.pop("text")                       # every network is a Story -> no text (Metricool rule)
            if "facebook" in nets: p["facebookData"] = fb("STORY")
            if "instagram" in nets: p["instagramData"] = {"type": "STORY", "isAiGenerated": False}
            out["story"] = p
    uses_tiktok = any(any(pr["network"] == "tiktok" for pr in p["providers"]) for p in out.values())
    return out, uses_tiktok
