# RiseUp Pakistan: operating guide for ChatGPT (GitHub connector + Metricool connector)

Repo: `mehrozshabir12-debug/riseup-posts` (branch `main`). Metricool brand **blogId `7305396`**, timezone **Asia/Karachi**.
Workflow: `.github/workflows/main.yml` ("RiseUp Media Manager").

You only ever **create text files**. You never upload images or videos, and you never run or dispatch the workflow yourself.

- **DO NOT edit** `template/`, `automation/` or `.github/`. These hold the owner's APPROVED design and the system code. If any approved file changes, the workflow refuses to render.
- **DO NOT** hand-edit `posted_log.json`, `celebrity_log.json`, `tribute_log.json` or `results/`. The workflow writes them.
- **Never open, read or send the owner's emails.**

## The loop (one news story)

**1. Read the rules first.** Read `POSTING_GUIDE.md`, then the tail of `posted_log.json`, `celebrity_log.json` and `tribute_log.json`, so you know today's counts and which stories are already done.

**2. Find a story.**
- Find ONE verified Pakistan story, first published in the **last 2 hours**. Use the article's own timestamp, in PKT.
- Sources: Dawn, Geo, ARY, Bol, Samaa, Express Tribune, Dunya, BBC Urdu, The News, Business Recorder, ProPakistani.
- Do not use rumours or claims that are not in the article.
- Death news needs **2 independent outlets**.

**3. Commit the request.** Commit `requests/<id>.json` to `main` (schema below). The `id` must equal the file name, for example `requests/2026-10-12-fia-helpline.json`. The commit starts the workflow automatically.

**4. Wait 3–10 minutes, then read `results/<id>.json`.**

| status | meaning | what you do |
|---|---|---|
| `rejected` | validation / duplicate / cap / stale / posting-hours problem; `errors` says why | fix it and commit a **new** file with a **new id** (or drop the story) |
| `failed` | rendering or the design check failed; nothing was posted | do not publish; report the `errors` |
| `awaiting_publish` | media is live on GitHub, payloads are ready | step 5 |
| `scheduled` / `published` / `partial` | already sent to Metricool (API mode) | only check the status (step 6) |

**5. Publish with the Metricool connector.** For **each** entry in `results.metricool.payloads` (`feed`, `reel`, `story`), call `createScheduledPost` with:
- `blogId`: `"7305396"`
- `date`: `payload.publicationDate.dateTime + "+05:00"`
- `info`: the payload object **exactly as given**, sent as a JSON string. Do not change networks, types, audio, covers, captions or `autoPublish`.

If `publicationDate` is already past or less than 3 minutes away, use now + 5 minutes for both `date` and `info.publicationDate.dateTime` (same time for feed, reel and story). Note each returned post id. The media URLs are public `raw.githubusercontent.com` links, so no upload is needed.
Optional music: before committing, put `"music": {"audioId": "<trending track>"}` in the request. If Metricool returns several candidates, retry with the exact numeric id.

**6. Verify, then commit a receipt.**
- After the publish time (wait at least 5 minutes past it), call `getScheduledPosts` for that day and read each provider's `status`.
- Commit `receipts/<id>.json` (see `automation/examples/receipt_example.json`):
  ```json
  {"id": "<id>", "scheduled": "2026-10-12 16:10 PKT",
   "posts": {"feed":  {"metricool_id": 1, "status": {"facebook": "PUBLISHED"}, "public_urls": {"facebook": "https://…"}},
             "reel":  {"metricool_id": 2, "status": {"facebook": "PUBLISHED", "instagram": "PUBLISHED", "tiktok": "PENDING"}},
             "story": {"metricool_id": 3, "status": {"facebook": "PUBLISHED", "instagram": "PUBLISHED"}}}}
  ```
- Report only the real statuses: `PUBLISHED`, `PENDING`, `ERROR` or `SCHEDULED`. **Never write PUBLISHED for a network that is not published.**
- The workflow sets `published` only when every network is PUBLISHED. Otherwise it sets `partial`, `scheduled` or `publish_failed`.
- To update a receipt, edit the same file again; it is re-merged.

**7. Retry safely, at most 2 extra attempts.**
- Retry only when a network shows `ERROR`.
- Create **one** new post with the same payload, but put **only the failed networks** in `providers` and set a new time (now + 5 min).
- Never re-post a network that is already PUBLISHED or still PENDING; that would create a duplicate.
- Raise `attempts` in the receipt and record the new `metricool_id`.
- An Instagram Story "media … cannot be found" error is a known Metricool glitch: retry the IG Story once.

## Limits (the workflow enforces them; plan around them)
- **15** news per day, **3** star posts per day (only when there is genuine news), **TikTok max 8 per day**. When the TikTok cap is hit, TikTok is dropped from the payloads automatically.
- Posting hours: **10:00 AM – 11:59 PM PKT**. With `"publish": {"at": "auto"}` the slot is now + 20 min, and news posts are spaced about **30 min** apart. Outside posting hours, the post moves to the next day at 10:05.
- Normal news never repeats. Duplicates are caught by request id, source URL, or a similar headline (≥ 60% word overlap, last 3 days).
- Tribute (death): up to **3** respectful versions per person, and 2 sources on different websites are required.
- Freshness: older than 2 h gives a warning; older than 24 h is rejected (48 h for tributes).
- Every story gets an FB + IG Story automatically.

## Request schema: `requests/<id>.json`
```json
{
 "id": "2026-10-12-fia-helpline",
 "type": "news",
 "headline": "FIA launches a new helpline for online fraud complaints across Pakistan",
 "language": "Roman Urdu",
 "sources": [{"outlet": "Dawn", "url": "https://www.dawn.com/news/…", "published_at": "2026-10-12T15:00:00+05:00"}],
 "card": {"scene": "police", "head1": "FIA Helpline", "head2_hl": "Online Fraud", "head2": "Complaints",
          "kicker": "New Number Launched", "desc": "Citizens can now report scams directly to FIA",
          "source": "Dawn", "date": "12 Oct 2026"},
 "reel": {"type": "narrated",
          "intro_voice": "spoken intro (Urdu script for an Urdu voice, or English)",
          "segments": [{"text": "on-screen line with **yellow highlight**", "voice": "what the narrator says"}],
          "outro_question": "Kya aap ke saath kabhi online fraud hua?",
          "scenes": ["police", "tech", "security"]},
 "caption": "emoji headline\n\n• fact\n• fact\n\nQuestion? Comment mein batayein 👇\n\nSource: Dawn\n\n#RiseUpPakistan #…",
 "tiktok_title": "short title (max 90)",
 "music": {"audioId": "2991194837697937", "label": "Chase It (Instrumental) - JQ, The Red Collective"},
 "publish": {"at": "auto", "networks": ["facebook", "instagram", "tiktok"], "stories": true},
 "ai_generated": null
}
```

**Top-level fields**
- `type`: `news` | `star` | `tribute`.
  - `star` and `tribute` also need `"person": {"name": "…", "handle": "@… only if confirmed"}`.
  - Star posts have no Reel.
- `language`: `Roman Urdu` | `English`. Use a mix through the day, as `POSTING_GUIDE.md` says.

**`card`**: the approved bold layout. Required: `scene`, `head1`, `head2_hl` or `head2`, `source`, `date`. Character limits:

| field | max chars |
|---|---|
| `head1` | 30 |
| `head2_hl` | 24 |
| `head2` | 30 |
| `kicker` | 40 |
| `desc` | 110 |

- **Scenes:** gold, fuel, electricity, currency, tax, people, heat, wind, rain, cricket, health, education, police, government, world, aviation, animal, tech, water, trade, general, entertainment, tribute, ribbon, cinema, music, hospital, virus, prison, security, trophy.
- Do not reuse a scene from the last 3 posts or one already used today. The run shows a warning if you do.
- `seed` is optional; it reproduces an exact graphic.
- `photo` is not allowed.

**`reel.type`**
- `narrated`: one-story Reel, at most 60 s. It opens on the news card (also the cover), then each segment has the approved text style over changing topic scenes, with narration and a breaking-news sting.
  - 2–6 `segments`; on-screen `text` max 190 characters.
  - Narration voices: Urdu `ur-PK-AsadNeural` by default (write `voice` lines in **Urdu script** for natural Urdu), or English `en-GB-RyanNeural` (when `language` is English). Override with `"voice"`.
  - If the narration fails or runs too long, the system uses the approved zoom Reel instead and adds a warning.
- `zoom`: the original 8 s zoom Reel. On IG, music comes from `music.audioId`.
- `anime`: the original anime Reel. Needs `paragraphs` (3–6, `**bold**` highlights), plus `mood` and `question`.
- `none`: no Reel.

**`ai_generated`**: leave it `null` for automatic honest labelling. A narrated Reel (synthetic voice) is marked AI on IG/TikTok; the graphics-only posts are not. Use `true`/`false` to override.

More examples are in `automation/examples/`.

## If something breaks
- Check the Actions tab, run "RiseUp Media Manager". The run summary lists each request's status. A failed request also fails the run (red ❌), so failures are visible.
- `results/<id>.json → errors / warnings` has the details.
- Optional API mode: when the owner adds GitHub Secrets `METRICOOL_USER_TOKEN` and `METRICOOL_USER_ID`, the workflow schedules by itself and checks status every 30 min. In that mode you only commit requests.
