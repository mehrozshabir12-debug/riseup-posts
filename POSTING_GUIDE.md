# RiseUp Pakistan – automatic news posting guide

Brand: RiseUp Pakistan (Metricool blogId 7305396). Networks: facebook, instagram, tiktok.
Language: Roman Urdu or English captions (see Caption language). Audience: Pakistan. Timezone for scheduling: Asia/Karachi.

## Each run
1. Read `posted_log.json` so no story is repeated (same event = skip, even from another outlet).
2. Find the most TRENDING Pakistan news of the last 12–24 hours — stories most people are talking about and will
   share (goal: maximum views and followers). Check what several outlets are all covering at once. Sources:
   BBC Urdu/BBC News, Dawn, Geo News, ARY News, Bol News, Samaa, Express Tribune, The News, Dunya News, 92 News,
   Sky News, Al Jazeera, Reuters, Business Recorder, APP, Radio Pakistan, ProPakistani, The Nation.
   Strong performers: cricket/PSL, petrol & electricity prices, gold & dollar rates, weather alerts, big government
   decisions, public holidays, jobs/education, viral national stories. Do 5 posts per run, best story first.
   Mix topics: economy, weather, energy, water, sports, tech, national, education, health.
   Avoid unverified rumours, graphic violence, and one-sided political attacks. Every number must come from the source.
3. For each story write a config JSON for `template/make_post.py`:
   - `scene` (NOT `theme`): pick the scene that fits the story best — gold, fuel, electricity, currency, tax, people,
     heat, wind, rain, cricket, health, education, police, government, world, aviation, animal, tech, water, trade,
     general, entertainment, tribute, ribbon, cinema, music, hospital, virus, prison. See "Image variety" below.
   - `line1` (yellow bar, 2–4 words), `line2` (big white, 2–4 words), `sub` (white, ~6–9 words), `sub_hl` (yellow tail, 1–3 words), `tag` (e.g. "Official finance update")
   Render: `python3 template/make_post.py cfg.json posts/YYYY-MM-DD-slug.jpg`. Look at the image; fix overflow.
4. Commit and push the images + updated `posted_log.json` to `main`.
   Public URL: `https://raw.githubusercontent.com/mehrozshabir12-debug/riseup-posts/main/posts/<file>.jpg`
5. Schedule each post with Metricool `createScheduledPost` (blogId 7305396, providers facebook+instagram+tiktok,
   facebookData {type: POST}, instagramData {type: POST, isAiGenerated: false},
   tiktokData {privacyOption: PUBLIC_TO_EVERYONE, title: <headline>}, autoPublish true).
   Caption: emoji + headline, 2–4 short lines/bullets of facts in own words, "Source: <outlet>", 6–8 hashtags starting with #RiseUpPakistan.
6. Never open, read or send the user's emails.

## Image variety (no repeated look) — OWNER'S STRICT RULE
The owner has complained twice (8 Oct 2026) about repeated images: one coins/chart image on 3 posts, the
star/spotlight image on 3 showbiz posts (Pinktober, Nana Patekar legacy, Asim Azhar's dad), the red cross on 2 health posts.
Rules:
- A scene may be used ONLY ONCE PER DAY across all posts (news, star, tribute). make_post.py prints
  "ALREADY USED TODAY" if you break this — then pick another scene. No exceptions, not even for similar stories.
- The picture must show what the story is about, not just its category:
  - Pinktober / breast cancer / awareness days → ribbon
  - films, dramas, actors' careers, film legacy → cinema
  - songs, singers, Coke Studio, concerts, dance to a song → music
  - celebrity award / general fame story → entertainment (only one per day)
  - deaths / condolence → tribute
  - doctors, hospitals, strikes, health system → hospital; outbreaks, dengue, polio, plague → virus; general health → health
  - jails, inmates, arrests → prison; crime / law and order → police
  - economy: gold, currency, tax, trade, people, government (each only once a day)
  - weather: rain / wind / heat / water; energy: electricity / fuel; international: world / aviation / trade
- If every fitting scene is already used today, use a real photo from the source (`photo` in the config, if it is
  licensed for reuse) or `general` with a clearly different palette — never a repeat.
- Look at the rendered image next to today's earlier images; if any look alike, re-render with another scene.
- Log the `scene` and `seed` that make_post.py prints in posted_log.json / celebrity_log.json / tribute_log.json for every post.

## Reel cover / thumbnail (OWNER'S RULE — more clicks)
Every Reel (Instagram REEL, Facebook REEL, TikTok video — zoom Reels, anime Reels and tribute Reels) must use the
story's own content image as its cover, never a random video frame. In the Metricool `info` of every post that has a
video, add:
  "videoThumbnailUrl": "https://raw.githubusercontent.com/mehrozshabir12-debug/riseup-posts/main/posts/<file>-story.jpg"
(the 9:16 -story.jpg with the headline, made by make_story.py — push it to main BEFORE scheduling so the URL works).
Never add videoThumbnailUrl to a STORY or an image-only post (Metricool rejects it). If Metricool rejects the cover,
schedule the Reel without it and mention it in the report.

## Music on Instagram and TikTok (more reach)
Schedule each story as TWO Metricool posts at the same time:
- **Facebook + TikTok** — the JPG image. tiktokData must include `"autoAddMusic": true` (TikTok adds a fitting
  track to photo posts automatically).
- **Instagram Reel** — make the video first: `python3 template/make_video.py posts/<file>.jpg posts/<file>.mp4`
  (8 s, 1080x1920, slow zoom), commit it, use its raw.githubusercontent.com URL as media.
  instagramData: `{"type": "REEL", "showReelOnFeed": true, "isAiGenerated": false,
  "audioConfiguration": {"audioId": "<search term>", "audioVolume": 100, "videoVolume": 0}}`.
  **Trending music first:** at the start of each run, web-search what is trending right now ("trending Instagram
  Reels audio this week", "trending TikTok sounds Pakistan this week") and use a currently trending track's title /
  artist as the search term. Prefer tracks whose mood fits the story (no upbeat party song on sad or crime news —
  use calm instrumental there). If the trending track is not in the catalog (business accounts get a limited
  library), use the closest candidate Metricool offers, else an upbeat popular instrumental.
  **ONLY real music, NEVER voice / "original_sound" (owner complaint 9 Oct 2026):** the 10:15 tyres Reel got
  "Someday We Will Dream About Today" as audioType "original_sound" from a random account
  (@comissaodeprojetosfousp) — it was a person talking in a foreign language. After scheduling, read the response:
  `audioConfiguration.audioType` MUST be "music" (with a displayArtist). If it is "original_sound" or anything else,
  immediately update the post with a different track (an instrumental from the "music" catalog), or remove the
  audioConfiguration. Prefer instrumental tracks (no lyrics in foreign languages). Never pick a candidate that has an
  igUsername instead of a displayArtist.
  NEVER repeat a track used earlier today (log `music` for every post and check the log first).
  If Metricool rejects it with a list of candidates, retry once with the best-fitting candidate's numeric id. If audio
  still fails, schedule the Reel without audioConfiguration rather than skipping the post.
- TikTok and Facebook: the API cannot pick a specific song. TikTok photo posts use `autoAddMusic: true` (TikTok
  adds a popular fitting track itself); Facebook gets no added music.

## Stories on Instagram and Facebook (every news post)
Each news story ALSO goes to Stories, at the same time as its posts:
- Make the story image: `python3 template/make_story.py posts/<file>.jpg posts/<file>-story.jpg` (1080x1920), look at it,
  commit it with the post files.
- Schedule ONE extra Metricool post: providers facebook + instagram, media = raw URL of the -story.jpg,
  facebookData {type: STORY}, instagramData {type: STORY, isAiGenerated: false}, NO text (stories have no caption),
  autoPublish true, same date/time as the story's feed post.
- TikTok has no Stories through Metricool, so TikTok gets only the normal photo post.
- If Metricool rejects the Story (plan/post limit or account type), still keep the feed posts and report it.
- Star posts ALSO get a Story: make the -story.jpg the same way and schedule facebook + instagram STORY at the same
  time with `"autoPublish": false` (manual-photo mode, so the owner can add the star's photo before publishing).
- Every post on every network that supports Stories must have its Story — never skip it.

## Anime Reels: 3 per day (Instagram Reels + TikTok + Facebook Reels)
Every day make EXACTLY 3 hand-painted anime-style news videos (count entries with `"anime": true` in today's
posted_log.json). At most one per run, for the run's most shareable story. Slots: the 1st in any run from 9:50 AM,
the 2nd only from the 2:50 PM run, the 3rd only from the 7:50 PM run (if a slot's run had no fresh story, the next run
makes it). The anime story still counts as one of the 15 news stories.
1. Write `posts/<date>-<slug>-anime.json`:
   `{"line1","line2","sub","sub_hl","tag"` (same as the post image), `"paragraphs"`: 3-5 short paragraphs (15-30 words
   each, own words, same language as the caption; wrap key numbers/words in **double stars** for the yellow box),
   `"question"`, `"source"`, `"mood"`: day / spring / sunset / rain / night to fit the story (rain for rain news,
   night for evening stories, etc.)}
2. Render: `python3 template/make_anime_reel.py posts/<file>-anime.json posts/<file>-anime.mp4` (takes ~3 min; it has its
   own nature sound + soft piano, 20-60 s). Extract a frame or two with ffmpeg and look at them.
3. Commit the .json + .mp4. Schedule ONE Metricool post with the MP4 at the story's time:
   providers facebook + instagram + tiktok, facebookData {type: REEL}, instagramData {type: REEL, showReelOnFeed: true,
   isAiGenerated: false} plus the audioConfiguration from rule 8 below, tiktokData {privacyOption:
   PUBLIC_TO_EVERYONE, title: <headline>, autoAddMusic: false}, text = the story caption.
4. For that story this REPLACES the normal Instagram zoom-Reel and the TikTok photo post: schedule the JPG only to
   facebook (type POST), plus the Story as usual. Log `"anime": true, "anime_video": "posts/..-anime.mp4"`.
5. Never name "Ghibli"/Studio Ghibli in captions or hashtags; never draw real people.
6. Keep exactly this look (approved by the owner on 8 Oct 2026): post-style logo and text, painted scene, own sound.
7. NO REPEATS: each anime video must use a different `mood` from the previous anime video, and the 3 videos of a
   day must all have different moods (day / spring / sunset / rain / night). Never reuse a `seed`. Log `mood` and
   `seed` in posted_log.json.
8. Music on the anime video: on Instagram add a trending track (see Music section) with
   `"audioConfiguration": {"audioId": ..., "audioVolume": 100, "videoVolume": 35}` so the nature sound stays softly
   underneath; TikTok `autoAddMusic: false` (the video already has sound); Facebook as is.

## TikTok daily limit (IMPORTANT)
TikTok blocks auto-posting after too many API posts in 24 h (error 40016, seen on 8 Oct 2026 after ~20 posts).
So TikTok gets at most 8 automatic posts per day: the 3 anime Reels first, then the 5 strongest news stories
(prices/bills, weather, cricket, viral). Log `"tiktok": true` for each one and count today's before adding TikTok.
Every other story goes to Facebook + Instagram only (drop "tiktok" from providers). Tribute Reels go to TikTok
as a separate post with `"autoPublish": false` (owner publishes from the app, which is not limited).
If Metricool shows error 40016 anyway, stop adding TikTok for the rest of the day and mention it in the report.

## Posting hours
All posts go out between 10:00 AM and 11:59 PM Pakistan time. Never schedule anything after 11:59 PM or before
10:00 AM (at the last run of the day, post only what still fits before midnight).

## Tribute package: death of a famous Pakistani or Indian actor (separate from everything else)
When a famous Pakistani or Indian actor dies and at least TWO established outlets (Dawn, Geo, BBC Urdu, The News,
Express Tribune, ARY, Samaa, etc.) confirm it, make on that same day — only once per person (check tribute_log.json):
1. **Post 1 (news):** scene `tribute` (candle). Hook like "Bollywood Mein Sog" / "Lollywood Mein Sog", name, cause/age
   only as reported.
2. **Post 2 (legacy):** a different scene (e.g. `entertainment`): career span, famous films, awards — facts from the sources.
3. **Reel:** anime Reel with `"sad": true` (mournful minor piano + soft strings, no birds; no extra Instagram track), mood sunset or night, 3-4 paragraphs
   (death as reported, career start, famous work/awards, the role people remember most), question like
   "<Name> ki aap ki pasandeeda film kaun si hai?".
   Never use the actor's real voice, film dialogue audio, film clips or photos (copyright) and never draw him/her.
   If the owner wants the actor's film dialogue/voice: make a copy without sound
   (`ffmpeg -i X.mp4 -f lavfi -i anullsrc=r=44100:cl=stereo -map 0:v -map 1:a -c:v copy -c:a aac -shortest X-nosound.mp4`)
   and schedule the Reel with `"autoPublish": false` and no audioConfiguration, so the owner adds the sound from the
   platform's own sound library in the app. Never download or rip film audio ourselves.
Schedule: post 1 about 10 min from now, the Reel 30 min later, post 2 30 min after that (within posting hours).
Each to facebook + instagram + tiktok (images: facebook+tiktok photo with autoAddMusic true, instagram as POST;
Reel: facebook REEL + instagram REEL + tiktok), plus facebook + instagram STORY for both images. Captions respectful,
in ENGLISH (owner's choice for death news: reel text, images and captions all English; anime cfg
`outro_label: "Your Thoughts?"`, `outro_cta: "Tell us in the comments and **Follow us**"`), "Source: <outlets>", hashtags #RiseUpPakistan #RIP<Name> etc. NEVER joke, never speculate.
These do NOT count toward the 15 news posts or the 3 anime Reels. Log them in tribute_log.json
(date, person, sources, files, scheduled times).

## Reach rules (owner's main goal: maximum reach)
- Hook first: `line1` must be a 2-4 word hook that makes people stop (e.g. "Petrol Phir Mehnga", "Barish Alert",
  "Bari Khabar") — never a dull label. The first 2 seconds of every Reel show it.
- Anime videos: aim for 25-40 s (3-4 short paragraphs); shorter videos get watched to the end, which drives reach.
- Music: trending track that fits the mood (see Music section) on Instagram; never the same track twice in a day.
- Captions: first line = the hook + emoji, then facts; end with a question so people comment; 6-8 relevant
  hashtags incl. #RiseUpPakistan and 1-2 broad ones (#Pakistan, #PakistanNews) — no hashtag stuffing.
- Prefer stories people share: prices/bills, weather, cricket, jobs, viral human stories.

## Caption language: mix of Roman Urdu and English (for reach)
Decide per story:
- **Roman Urdu** for stories that touch ordinary people's pockets and daily life, or are emotional / viral:
  petrol, bijli & gas bills, sone & dollar rates, mehngai, salaries, jobs, school/college news, weather alerts,
  holidays, cricket, crime/accidents (no gore), heart-touching stories (e.g. Madhubala). Write natural, simple
  Roman Urdu (e.g. "Petrol ki qeemat mein Rs 5 ka izafa! ⛽"), keep numbers and names exact.
- **English** for policy, business, IMF/FBR, international, technical or official-statement stories.
Roughly half and half across the day. In both languages end the caption with a short question to get comments,
e.g. Roman Urdu "Aap ka kya khayal hai? Comment mein batayein 👇" / English "What do you think? Tell us below 👇".
The post IMAGE text stays in English (template). Keep "Source: <outlet>" and the hashtags.

## Social media stars / celebrity posts (separate from the 15 news posts)
2–3 per day, logged in `celebrity_log.json` (NOT posted_log.json, so they never count toward the 15 news cap).
- Subjects: Pakistani social media stars, YouTubers, TikTokers, actors, singers, cricketers in the spotlight.
- Only real, recent (last 24 h) updates reported by established outlets (Dawn Images, Express Tribune
  Life & Style, Geo, ARY, Samaa, Bol, Dunya, BBC Urdu, Something Haute, Galaxy Lollywood) — new song/drama/film,
  milestones, awards, weddings/births they announced themselves, public statements, viral moments.
- Never: rumours, leaked/private content, insults or mockery, claims not in the source, anything about minors,
  political attacks. Write neutrally and kindly.
- Do NOT use photos of the person (copyright). Use scene `entertainment` (or `cricket` for cricketers); vary it per the "Image variety" rules.
- Captions mostly Roman Urdu, end with a question, "Source: <outlet>", hashtags starting #RiseUpPakistan.

### Star posts: tagging + AUTO-PUBLISH (owner's rule, 9 Oct 2026 — no more manual photo)
- **Tag the star**: add their official Instagram/TikTok handle (e.g. @username) in the caption ONLY if the handle
  is confirmed by the source article or the star's verified account. If not sure, do not tag — never guess.
- **Auto-publish**: the owner no longer adds photos by hand. Every star post and its Story are scheduled with
  `"autoPublish": true`, using our own rendered graphic (no photos of the person — copyright).
  Pick the scene that fits the story per "Image variety" (music for songs/singers, cinema for films/dramas,
  cricket for cricketers, entertainment for general fame/awards — each scene only once per day).
- Schedule ONE Metricool post for facebook + instagram with the JPG (instagramData {type: POST}); add tiktok
  (tiktokData {autoAddMusic: true}) only if today's TikTok count is under the 8/day limit (see TikTok daily limit),
  and log `"tiktok": true` if added. Plus the facebook + instagram STORY with the -story.jpg, no text.
  No Reel/audio for star posts.
