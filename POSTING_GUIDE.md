# RiseUp Pakistan – automatic news posting guide

Brand: RiseUp Pakistan (Metricool blogId 7305396). Networks: facebook, instagram, tiktok.
Language: English captions. Audience: Pakistan. Timezone for scheduling: Asia/Karachi.

## Each run
1. Read `posted_log.json` so no story is repeated (same event = skip, even from another outlet).
2. Find fresh Pakistan news from the last 24 hours (WebSearch / WebFetch). Prefer reliable outlets:
   Dawn, The Express Tribune, Geo, The News, Business Recorder, APP, Radio Pakistan, ARY, The Nation, ProPakistani.
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
