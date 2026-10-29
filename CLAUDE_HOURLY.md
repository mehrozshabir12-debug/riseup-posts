RISEUP PAKISTAN — HOURLY RUNBOOK FOR CLAUDE (Runway photo version, 16 Oct 2026)
==============================================================================
Claude's scheduled task runs this at HH:45 PKT (09:45 ... 23:45). One verified story per slot.
Photo: Runway connector (mcp__Runway__generate_image, nano-banana-2-lite, 4 credits) -> card.photo_url. Design: GitHub renders the approved
card. Publishing: Claude's Metricool connector. Accuracy first; if any step fails, SKIP and REPORT.

Repo: mehrozshabir12-debug/riseup-posts (main). Metricool blogId 7305396, Asia/Karachi.
Never touch template/, automation/, .github/. Never edit/delete posts you did not create in this run;
never touch drafts you did not create. Never read or send the owner's e-mails.

0. TIME — DO THIS FIRST, EVERY RUN
----------------------------------
- Get the real current time and convert it to Pakistan time (PKT = UTC+05:00). Call it NOW.
- TARGET SLOT T = the next whole hour after NOW that is one of:
  10:00 11:00 12:00 13:00 14:00 15:00 16:00 17:00 18:00 19:00 20:00 21:00 22:00 23:00 00:00
  (between 00:01 and 09:59 the next slot is 10:00).
- The 23:45 run prepares 00:00 of the NEXT calendar date. That 00:00 post still belongs to the RiseUp day that
  started at 10:00 the day before. RISEUP DAY D = slots 10:00 D ... 23:00 D + 00:00 of D+1.
  All daily counts (15 news, 8 TikTok) are per RiseUp day, never per calendar date.
- RUN LOG path: runs/<calendar date of T>T<HHMM of T>.json. Examples: slot 15:00 on 14 Oct =
  runs/2026-10-14T1500.json; slot 00:00 closing 14 Oct = runs/2026-10-15T0000.json.
- Immediately commit the run log with {"slot": "<T ISO +05:00>", "outcome": "started",
  "run_started_pkt": "<NOW ISO>"}. You overwrite it at the end (section 7).
- Publication time: T itself. Never schedule anything in the past or less than 5 minutes from NOW.
  If NOW is already later than T−5 min, the post may go at NOW+5 min, but only until T+15 min;
  after that the slot is MISSED: outcome "skipped_slot_missed", stop.


1. CHECK METRICOOL BEFORE ANYTHING ELSE
---------------------------------------
- getBrandSettings once: confirm blogId 7305396, timezone Asia/Karachi and that Facebook, Instagram and TikTok
  are connected. If a network is missing, write it in the run log errors.
- getScheduledPosts for blogId 7305396, timezone Asia/Karachi, extendedRange FALSE, in SIX-HOUR windows
  (one call per window; a single big range exceeds the tool's size limit and fails):
  first T−1h..T+1h (slot check + previous slot), then the windows covering NOW−48 h .. NOW+12 h.
  If a window still says the result is too large, split that window in half and retry it.
  The duplicate check is complete only when every window succeeded; if any window keeps failing,
  outcome "error_metricool_history_incomplete" and stop (never post without a full duplicate check).
  From it note:
  a) whether a NON-Story post already exists at T (any creator, drafts included — but ignore posts whose text
     starts with "RISEUP PHOTO HOLDER"). If yes ->
     outcome "skipped_slot_taken", stop. One story per slot, never two.
  b) the stories of the last 48 h, to avoid duplicates (same event = duplicate, even from another outlet or with
     a new angle, unless there is a genuinely new development).
  c) today's counts for this RiseUp day: news feed posts (max 15) and posts that include TikTok (max 8).
     Drafts do not count.
  d) the PREVIOUS slot's posts (feed post at T−1 h and its Story at T−55 min): read each network's status.
     If a network shows ERROR, follow section 6. Record what you saw in the run log ("previous_slot_check").


2. FIND THE NEWS (web search, every run)
---------------------------------------
- Pakistan news, or world news that directly affects Pakistan (prices, fuel, Pakistanis abroad, cricket ...).
- FRESHNESS (owner's rule, 15 Oct 2026): the NEWEST suitable story wins. Search in widening windows before T and
  take the first window that has a story passing every other rule:
    1) published or substantively updated within 2 hours before T  (best)
    2) otherwise within 3 hours, then 4 hours, then 6 hours
    3) otherwise within 8 hours before T                           (maximum — never older)
  "Substantively updated" = new facts/figures, not a re-headline or minor edit. Within a window, pick the most
  important story for ordinary people. The story must still be new to our page (duplicate check, section 1b).
  Write the window used in the run log ("freshness_window": "2h" / "3h" / "4h" / "6h" / "8h").
  A timestamp later than NOW is impossible: re-check the time zone.
- Open the article itself and read its own published/updated timestamp (meta or byline). Convert it to PKT.
  Do NOT use search-snippet dates, "2 hours ago" labels or crawl dates. If you cannot establish the exact
  timestamp, the source does not count.
- VERIFICATION: either
  (a) 2 articles from 2 DIFFERENT approved outlets, both reporting the same facts, or
  (b) 1 official primary source (a *.gov.pk site, SBP, ISPR, PBS, OGRA, NEPRA, PTA, NADRA, FBR, ECP, PSX, PMD,
      NDMA, PCB).
  Approved outlets: Dawn (dawn.com), Express Tribune (tribune.com.pk), Geo News (geo.tv), The News
  (thenews.com.pk), Business Recorder (brecorder.com), APP (app.com.pk), PTV News (ptv.com.pk),
  BBC (bbc.com / bbc.co.uk), Reuters (reuters.com), AP (apnews.com), Al Jazeera (aljazeera.com),
  Arab News (arabnews.pk / arabnews.com). Any other website does not count.
  A wire story re-published by an outlet (e.g. "Express Tribune (Reuters)") is ONE source, not two.
  TIMESTAMPS — what is required where (clarified 15 Oct 2026):
  - The MAIN source (the one that makes the story fresh) needs its exact published/updated time from the
    article itself. Its date goes on the card.
  - The CONFIRMING source only has to report the same event with the same key facts (names, figures, place),
    published on the same day or later. Its exact minute is NOT required; its date is enough.
  - An official notification / press release that shows a date but no time counts as the official primary
    source when its date is today (PKT); a news article with an exact time then serves as the main source
    for freshness. If no article has an exact time, use the official item's date and the 8-hour rule cannot
    be proven -> do not use it.
- Cross-check every name, number, place, price and date between the sources before designing anything.
- Skip: rumours, "sources say", unconfirmed casualty figures, graphic violence, private individuals, stories about
  minors, one-sided political attacks. Politics: neutral and factual.
- Prefer stories that matter to ordinary people: prices, fuel, electricity, jobs, education, weather, health,
  cricket, economy, technology, major national decisions.
- A slot is skipped only when NOTHING from the last 8 hours passes all rules (verified, not a duplicate, safe).
  Then do NOT stop yet: go to section 2B (showbiz fallback). Only if 2B also finds nothing, outcome
  "skipped_no_fresh_verified_news", list the best rejected candidates (news AND showbiz) and why in the run
  log, stop. Never post old news to fill a slot. A skip is a correct result.


2B. SHOWBIZ FALLBACK — ONLY WHEN SECTION 2 FOUND NO NEWS (owner's rule, 30 Oct 2026)
-------------------------------------------------------------------------------------
- Use this ONLY after section 2 found no qualifying news for slot T. Never replace a qualifying news story.
- Subject: ONE update about the Pakistani showbiz industry (actors, singers, dramas, films, music) or a
  Pakistani YouTuber / TikToker / social media star: a new song, drama, film or trailer, an award, a milestone,
  a public statement, a wedding/birth the person announced themselves, a viral moment.
- SAME verification and freshness as section 2, no exceptions: 2 articles from 2 DIFFERENT approved outlets
  (Dawn incl. images.dawn.com, Express Tribune incl. Life & Style, Geo, The News, BBC, Arab News, APP ...),
  main source's exact timestamp read from the article itself, within 8 hours before T, not a duplicate of the
  last 48 h on Metricool or of celebrity_log.json. Entertainment-only sites (Something Haute, Galaxy Lollywood,
  Instagram / Facebook / YouTube posts, fan pages) can help you FIND a story but never count as a source.
- Never: rumours, "sources say", leaked or private content, fights/controversy/insults or mockery, divorce or
  relationship gossip, anything about minors, political attacks, claims not in the sources. Neutral and kind.
- Daily cap: max 3 showbiz posts per RiseUp day (the pipeline rejects a 4th). They do NOT count toward the
  15 news posts. If the cap is reached, skip as in section 2.
- Card, photo and caption as section 3, with these changes: the Runway photo must NOT show the person or any
  real identifiable face — use a fitting generic scene (concert stage, film set, drama shoot, recording studio,
  awards stage, a phone showing an unnamed video with anonymous people). Caption: same format as section 3; tag
  the star's official @handle ONLY if the handle is confirmed by a source article or their verified account.
- Request (section 4) with "type": "star", "person": {"name": "<full name>", "handle": "<@handle or empty>"},
  "reel": {"type": "none"} and NO "music" field (star posts get no Reel; the pipeline posts FB+IG photo,
  TikTok if under the daily limit, and the FB+IG Story). Then sections 5–7 as usual (skip the Reel/music checks).
- Run log: outcome "scheduled_showbiz_fallback", stages.news_search must still list why the news candidates
  failed, and add "fallback": "showbiz".


3. CARD TEXT, PHOTO AND CAPTION
------------------------------
Card text (only sourced facts; never round numbers): head1 (2-4 words, max 30), head2_hl (yellow box, 1-3 words,
max 24), head2 (0-2 words, may be ""), kicker (3-5 words, max 40), desc (one sentence, max 12 words),
source (outlet), date ("DD MON YYYY" = earliest source's PKT publication date).
PHOTO — Runway connector, CHEAPEST model, ONE image per run (owner: spend as few credits as possible):
  ORDER RULE (owner, 25 Oct 2026): generate the photo ONLY AFTER the story has fully passed section 2
  (freshness incl. the first-report time of the event, two approved sources, all content rules) and the card
  text is written. Never call mcp__Runway__generate_image while any check is still open or a skip is possible.
  mcp__Runway__generate_image(model "nano-banana-2-lite", ratio "4:3", promptText = one realistic scene of the
  story: place, objects, anonymous ordinary people, natural light, ending with "Absolutely no text, letters,
  numbers, signs, logos or watermarks anywhere in the image."). Then mcp__Runway__get_task until it has "url".
  No real identifiable people (politicians, officials, celebrities, athletes), no brand logos unless the story is
  about that company, no violence/injury/weapons. Look at the image: retry ONCE only if it shows readable text,
  a real public figure, gore or a clear distortion. Never use another model.
  If the result says credits are too low: outcome "error_runway_credits", stop (do not post without a photo).
MUSIC (owner's order 17 Oct 2026: Instagram Reels with music are back — almost all Instagram views came from Reels):
  Pick ONE track per story for the Instagram Reel. Web-search what is trending now ("trending Instagram Reels audio
  this week", "trending sounds Pakistan this week") and use a trending track's "title artist" as music.audioId (a
  search term), or a numeric Metricool audio id. Mood must fit the story: calm instrumental for sad, crime, disaster
  or serious news; upbeat only for good news, cricket wins, prices falling. Prefer instrumentals (no foreign-language
  lyrics). Never the same track twice in one RiseUp day: read "music" in today's runs/*.json first.
  VERIFIED MUSIC LIST (owner complaint 17 Oct 2026: a Reel went out with NO sound because the trending search
  term only matched "original_sound"). These numeric ids are known Instagram "music" tracks. If the trending search
  term is not confirmed as audioType "music", use a NUMERIC id from this list instead (one not used today):
    calm / serious news: 478728841591377 Reflection - Sam Marshall | 1329928372147056 Slow Living - stereogully |
      1211414204067053 Drift Away (Instrumental) - Giulio Cercato | 589750179694057 Float (Instrumental) - Sleeping Lion |
      985048086988929 Vow (Instrumental) - Ross Lara | 1362869204224018 Purity - Ross Lara |
      297072506536797 Melodic Mountain - Ross Lara | 1197857668796525 Carry On (Instrumental) - Giulio Cercato |
      1142425671382048 Painted White - Julia Gartha | 1368174622072131 Fairytales Age Too - cloud cover
    neutral / economy: 757785052896581 Sunday In October - Trout Recording | 810120545333296 Iced Latte - Global Genius |
      934661001819759 Cafe Lovers - Global Genius | 1131479132514825 Simple Pleasures - Alex Blue |
      614418411270205 A Little Love Song - Alex Blue | 836981678209890 I'll Always Be Around - Alex Blue |
      2384396914990297 City Around The Corner - The Poison Oaks
    upbeat / good news / cricket: 581639516835198 Upside Down - Mike Block | 1543577430102877 The Process - Jackson Whalan |
      1274149560124013 Heros Journey (Instrumental) - Abby Posner | 336015428971390 Glow (Instrumental) - KNOTTS |
      2479868452044482 Out In The Wild - bldgs | 2991194837697937 Chase It (Instrumental) - JQ, The Red Collective
  A Reel must NOT go out silent: try up to 3 list ids before ever removing the audio.
  Only the Instagram Reel gets this music. TikTok photo posts keep autoAddMusic (TikTok picks); Facebook gets none.
  Anime and narrated Reels stay OFF (reel.type is always "zoom" — the 8 s zoom video is rendered free by GitHub).
Caption: 2-3 short English sentences naming the outlet; blank line; "Image: AI-generated illustration.";
blank line; exactly 5 hashtags including #RiseUpPakistan. No links. tiktok_title max 90 characters.


4. REQUEST
----------
Commit requests/<id>.json to main (id = <RiseUp day date>-<slug>; file name = id; never reuse an id):
{"id": "...", "type": "news", "headline": "<one full factual sentence>", "language": "English",
 "sources": [{"outlet": "...", "url": "https://...", "published_at": "<ISO +05:00>"}, ...],
 "card": {"photo_url": "<the Runway url, copied exactly>", "head1": "...", "head2_hl": "...", "head2": "...", "kicker": "...",
          "desc": "...", "source": "...", "date": "DD MON YYYY"},
 "caption": "...", "tiktok_title": "...",
 "publish": {"slot": "<T ISO +05:00>", "networks": ["facebook", "instagram", "tiktok"], "stories": true,
             "dry_run": <true in TEST MODE>},
 "reel": {"type": "zoom"}, "music": {"audioId": "<track search term or numeric id>", "label": "<title - artist>"},
 "ai_generated": true}


5. WAIT, CHECK, PUBLISH
-----------------------
- Poll results/<id>.json on main every 60 s, up to 10 min (git pull or gh api).
  rejected/failed -> copy errors to the run log (outcome error_rejected / error_render_failed). If the photo could not be
  downloaded, re-run get_task for a fresh url and commit ONE new request with a NEW id. Then stop.
- awaiting_publish / dry_run_ready -> download results.media.feed and LOOK at it: every word, figure, date and
  source correct; photo realistic with no text, logos or identifiable public figures; no distortions.
  Anything wrong -> do not publish, outcome error_card_check.
- awaiting_publish also gives results.media.reel (the zoom MP4). Open it once to confirm it plays and shows the card.
- Feed: createScheduledPost(blogId "7305396", date = payloads.feed.publicationDate.dateTime + "+05:00",
  info = payloads.feed exactly) — Facebook + TikTok photo. Reel: same with payloads.reel — the Instagram Reel with
  music. Story: same with payloads.story. TEST MODE: add "draft": true to all three.
- MUSIC CHECK (owner complaint 9 Oct: a Reel once got a stranger talking in a foreign language): read the Reel's
  createScheduledPost response / getScheduledPosts entry. instagramData.audioConfiguration.audioType MUST be
  "music" with a displayArtist. If it is "original_sound", has an igUsername instead of a displayArtist, or Metricool
  rejected the audio with a candidate list: updateScheduledPost with the best candidate whose audioType is "music";
  if there is none, use a numeric id from the VERIFIED MUSIC LIST (section 3) that fits the mood and is unused today,
  and check again. Up to 3 tries. Only if all 3 fail, update the Reel to have no audioConfiguration (the post must
  still go out) and write "error_reel_silent" in the run log errors. Write the final track in the run log as "music".
- getScheduledPosts T-5 min..T+10 min: feed, Reel and Story exist, providers PENDING, media = raw.githubusercontent
  card / MP4.
- Commit receipts/<id>.json {"id", "scheduled", "posts": {"feed": {"metricool_id", "status"}, "reel": {...}, "story": {...}}}
  with the real statuses only.


6. VERIFY AND RETRY (at the start of each run, for the previous slot)
--------------------------------------------------------------------
- PUBLISHED: note the publicUrl in the run log.
- ERROR: retry ONCE now, at most 2 retries in total per network: createScheduledPost with the same image and
  text, providers = ONLY the failed networks (keep only those networks' data), time = NOW+5 min.
  Never re-post a network that is PUBLISHED or PENDING (that creates a duplicate).
  Instagram Story "The media is not ready for publishing, please wait for a moment" is an Instagram processing
  delay: the retry at NOW+5 min is the fix. TikTok error 40016 (daily limit) = no more TikTok that RiseUp day.
  To reuse the image for a retry, use the link from the original post's "media".


7. FINISH: OVERWRITE THE RUN LOG (every run, including skips)
---------------------------------------------------------------
Commit runs/<...>.json (same path as section 0):
{"slot": "...", "riseup_day": "YYYY-MM-DD", "run_started_pkt": "...", "run_finished_pkt": "...",
 "test_mode": true|false,
 "outcome": "scheduled | scheduled_showbiz_fallback | scheduled_as_draft | skipped_no_fresh_verified_news | skipped_slot_taken |
             skipped_slot_missed | skipped_daily_cap | error_<short reason>",
 "story": {"headline": "...", "sources": [{"outlet": "...", "url": "...", "published_at": "<ISO +05:00>"}]},
 "request_id": "...", "card_url": "<results.media.feed>",
 "image_attempts": [{"attempt": 1, "result": "ok | text in photo | refused: <message>"}],
 "metricool": {"feed": {"id": 0, "plannerUrl": "...", "networks": {"facebook": "PENDING", "instagram": "PENDING", "tiktok": "PENDING"}},
               "reel": {"id": 0, "plannerUrl": "...", "networks": {"instagram": "PENDING"}},
               "story": {"id": 0, "plannerUrl": "...", "networks": {"facebook": "PENDING", "instagram": "PENDING"}}},
 "music": "<title - artist actually attached, or none>",
 "stages": {"metricool_read": "...", "previous_slot_check": "...", "news_search": "...", "verification": "...",
            "image": "...", "publish": "..."},
 "skipped_candidates": [{"headline": "...", "reason": "..."}],
 "errors": ["exact error text from any tool call"]}
If a tool (web search, image generation, GitHub, Metricool) is not available or returns an error, write outcome
"error_tool_unavailable: <tool>" with the exact message. A GitHub watchdog fails at HH:55 when this file is missing
or still says "started", and GitHub e-mails the owner.
Do not message the owner for routine success. Do message on any outcome starting with "error".
