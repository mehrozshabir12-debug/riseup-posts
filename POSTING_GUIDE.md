# RiseUp Pakistan – automatic news posting guide

Brand: RiseUp Pakistan (Metricool blogId 7305396). Networks: facebook, instagram, tiktok.
Language: English captions. Audience: Pakistan. Timezone for scheduling: Asia/Karachi.

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
     general, entertainment. See "Image variety" below.
   - `line1` (yellow bar, 2–4 words), `line2` (big white, 2–4 words), `sub` (white, ~6–9 words), `sub_hl` (yellow tail, 1–3 words), `tag` (e.g. "Official finance update")
   Render: `python3 template/make_post.py cfg.json posts/YYYY-MM-DD-slug.jpg`. Look at the image; fix overflow.
4. Commit and push the images + updated `posted_log.json` to `main`.
   Public URL: `https://raw.githubusercontent.com/mehrozshabir12-debug/riseup-posts/main/posts/<file>.jpg`
5. Schedule each post with Metricool `createScheduledPost` (blogId 7305396, providers facebook+instagram+tiktok,
   facebookData {type: POST}, instagramData {type: POST, isAiGenerated: false},
   tiktokData {privacyOption: PUBLIC_TO_EVERYONE, title: <headline>}, autoPublish true).
   Caption: emoji + headline, 2–4 short lines/bullets of facts in own words, "Source: <outlet>", 6–8 hashtags starting with #RiseUpPakistan.
6. Never open, read or send the user's emails.

## Image variety (no repeated look)
The owner does not want posts that look the same. Rules:
- Use `scene` in the config. Each scene is drawn with a random seed, so colours, layout and details change every render.
- Never use the same scene as any of the last 3 posts (news + star posts). make_post.py prints a WARNING if you do —
  then pick the next-best fitting scene (e.g. economy story: currency / tax / trade / people / gold / government;
  weather: rain / wind / heat / water; energy: electricity / fuel; international: world / aviation / trade).
- Only when the story truly needs it (e.g. two gold-price posts) may a scene repeat, and then not back-to-back.
- Look at the rendered image and the previous post's image side by side; if they look alike, re-render.
- Log the `scene` and `seed` that make_post.py prints in posted_log.json / celebrity_log.json for every post.

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
posted_log.json). At most one per run, for the run's most shareable story. Slots: the 1st in any run from 1:50 PM,
the 2nd only from the 4:50 PM run, the 3rd only from the 7:50 PM run (if a slot's run had no fresh story, the next run
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

### Star posts: tagging + manual photo (overrides the scheduling rules above for star posts)
- **Tag the star**: add their official Instagram/TikTok handle (e.g. @username) in the caption ONLY if the handle
  is confirmed by the source article or the star's verified account. If not sure, do not tag — never guess.
- **Manual-photo mode**: schedule ONE Metricool post for facebook + instagram + tiktok with the JPG, with
  `"autoPublish": false` (Metricool then sends the user a push notification at the scheduled time so they can add
  the star's photo and publish by hand). instagramData {type: POST}, tiktokData {autoAddMusic: true}.
  No Reel/audio for star posts. Do not make the MP4. Do make the Story (see Stories section).
