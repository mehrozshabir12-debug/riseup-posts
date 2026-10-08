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
   - `theme`: one of economy, weather, energy, water, sports, tech, general
   - `line1` (yellow bar, 2–4 words), `line2` (big white, 2–4 words), `sub` (white, ~6–9 words), `sub_hl` (yellow tail, 1–3 words), `tag` (e.g. "Official finance update")
   Render: `python3 template/make_post.py cfg.json posts/YYYY-MM-DD-slug.jpg`. Look at the image; fix overflow.
4. Commit and push the images + updated `posted_log.json` to `main`.
   Public URL: `https://raw.githubusercontent.com/mehrozshabir12-debug/riseup-posts/main/posts/<file>.jpg`
5. Schedule each post with Metricool `createScheduledPost` (blogId 7305396, providers facebook+instagram+tiktok,
   facebookData {type: POST}, instagramData {type: POST, isAiGenerated: false},
   tiktokData {privacyOption: PUBLIC_TO_EVERYONE, title: <headline>}, autoPublish true).
   Caption: emoji + headline, 2–4 short lines/bullets of facts in own words, "Source: <outlet>", 6–8 hashtags starting with #RiseUpPakistan.
6. Never open, read or send the user's emails.

## Music on Instagram and TikTok (more reach)
Schedule each story as TWO Metricool posts at the same time:
- **Facebook + TikTok** — the JPG image. tiktokData must include `"autoAddMusic": true` (TikTok adds a fitting
  track to photo posts automatically).
- **Instagram Reel** — make the video first: `python3 template/make_video.py posts/<file>.jpg posts/<file>.mp4`
  (8 s, 1080x1920, slow zoom), commit it, use its raw.githubusercontent.com URL as media.
  instagramData: `{"type": "REEL", "showReelOnFeed": true, "isAiGenerated": false,
  "audioConfiguration": {"audioId": "<search term>", "audioVolume": 100, "videoVolume": 0}}`.
  Pick the search term at random from upbeat, popular instrumental / news-background tracks (vary it every post).
  If Metricool rejects it with a list of candidates, retry once with the first candidate's numeric id. If audio
  still fails, schedule the Reel without audioConfiguration rather than skipping the post.

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
- Do NOT use photos of the person (copyright). Use theme `entertainment` (or `sports` for cricketers).
- Captions mostly Roman Urdu, end with a question, "Source: <outlet>", hashtags starting #RiseUpPakistan.

### Star posts: tagging + manual photo (overrides the scheduling rules above for star posts)
- **Tag the star**: add their official Instagram/TikTok handle (e.g. @username) in the caption ONLY if the handle
  is confirmed by the source article or the star's verified account. If not sure, do not tag — never guess.
- **Manual-photo mode**: schedule ONE Metricool post for facebook + instagram + tiktok with the JPG, with
  `"autoPublish": false` (Metricool then sends the user a push notification at the scheduled time so they can add
  the star's photo and publish by hand). instagramData {type: POST}, tiktokData {autoAddMusic: true}.
  No Reel/audio for star posts. Do not make the MP4.
