"""Offline tests for slot timing, RiseUp-day accounting, freshness, verification, payloads.
Run:  python3 -m unittest automation/tests/test_pipeline.py -v      (no network, no Metricool calls)
"""
import datetime as dt, os, sys, unittest
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import slots, payloads, common                     # noqa: E402

PKT = slots.PKT
P = lambda s: dt.datetime.fromisoformat(s)


def req(**over):
    r = {"id": "2026-10-14-test-story", "type": "news",
         "headline": "Test headline sentence used only by the offline test suite",
         "language": "English",
         "sources": [{"outlet": "Dawn", "url": "https://www.dawn.com/news/1", "published_at": "2026-10-14T14:20:00+05:00"},
                     {"outlet": "Geo News", "url": "https://www.geo.tv/latest/2", "published_at": "2026-10-14T14:35:00+05:00"}],
         "card": {"scene": "fuel", "head1": "Test Head", "head2_hl": "Rs 1", "head2": "Per Litre", "kicker": "Kicker",
                  "desc": "Short summary", "source": "Dawn", "date": "14 OCT 2026"},
         "caption": "Two short sentences about the story, naming Dawn. Source: Dawn\n\n#RiseUpPakistan #a #b #c #d",
         "publish": {"slot": "2026-10-14T15:00:00+05:00", "networks": ["facebook", "instagram", "tiktok"], "stories": True},
         "reel": {"type": "none"}}
    r.update(over)
    return r


class Slots(unittest.TestCase):
    def test_next_slot(self):
        self.assertEqual(slots.next_slot(P("2026-10-14T09:45:00+05:00")), P("2026-10-14T10:00:00+05:00"))
        self.assertEqual(slots.next_slot(P("2026-10-14T14:45:00+05:00")), P("2026-10-14T15:00:00+05:00"))
        self.assertEqual(slots.next_slot(P("2026-10-14T23:45:00+05:00")), P("2026-10-15T00:00:00+05:00"))
        self.assertEqual(slots.next_slot(P("2026-10-15T00:45:00+05:00")), P("2026-10-15T10:00:00+05:00"))

    def test_midnight_belongs_to_previous_day(self):
        self.assertEqual(slots.riseup_day(P("2026-10-15T00:00:00+05:00")), dt.date(2026, 10, 14))
        self.assertEqual(slots.riseup_day(P("2026-10-14T10:00:00+05:00")), dt.date(2026, 10, 14))
        d = slots.day_slots(dt.date(2026, 10, 14))
        self.assertEqual(len(d), 15)
        self.assertEqual(d[-1], P("2026-10-15T00:00:00+05:00"))

    def test_chatgpt_rrule_in_perth_hits_every_preparation_time(self):
        # RRULE:FREQ=DAILY;BYHOUR=0,1,2,12..23;BYMINUTE=45, interpreted in Australia/Perth
        perth = ZoneInfo("Australia/Perth")
        runs = set()
        for h in (0, 1, 2, *range(12, 24)):
            t = dt.datetime(2026, 10, 15 if h < 12 else 14, h, 45, tzinfo=perth).astimezone(PKT)
            runs.add(t.strftime("%H:%M"))
        self.assertEqual(runs, {f"{h:02d}:45" for h in range(9, 24)})
        # Perth 02:45 (15 Oct) = PKT 23:45 (14 Oct) -> prepares 00:00 15 Oct, which is RiseUp day 14 Oct
        t = dt.datetime(2026, 10, 15, 2, 45, tzinfo=perth).astimezone(PKT)
        self.assertEqual(slots.riseup_day(slots.next_slot(t)), dt.date(2026, 10, 14))

    def test_tiktok_quota_spreads_8_over_the_day(self):
        q = lambda h, d=14: slots.tiktok_quota(dt.datetime(2026, 10, d, h, tzinfo=PKT))
        self.assertEqual([q(10), q(11), q(12), q(13), q(23), q(0, 15)], [1, 1, 2, 2, 7, 8])

    def test_publication_time(self):
        s = P("2026-10-14T15:00:00+05:00")
        self.assertEqual(slots.publication_time(s, P("2026-10-14T14:45:00+05:00")), s)
        self.assertEqual(slots.publication_time(s, P("2026-10-14T14:58:20+05:00")), P("2026-10-14T15:04:00+05:00"))
        self.assertIsNone(slots.publication_time(s, P("2026-10-14T15:12:00+05:00")))
        self.assertEqual(slots.story_time(s), P("2026-10-14T15:05:00+05:00"))


class Sources(unittest.TestCase):
    def test_verification(self):
        ok = lambda *u: slots.verification([{"url": x} for x in u])[0]
        self.assertTrue(ok("https://www.dawn.com/a", "https://www.geo.tv/b"))
        self.assertFalse(ok("https://www.dawn.com/a", "https://www.dawn.com/b"))         # same outlet twice
        self.assertFalse(ok("https://www.dawn.com/a"))
        self.assertTrue(ok("https://www.finance.gov.pk/x"))                                # official
        self.assertTrue(ok("https://www.sbp.org.pk/press/1"))
        self.assertFalse(ok("https://www.dawn.com/a", "https://randomblog.pk/b"))          # unapproved site
        self.assertFalse(ok("https://facebook.com/x", "https://www.geo.tv/b"))

    def test_freshness_relative_to_slot(self):
        slot, now = P("2026-10-14T15:00:00+05:00"), P("2026-10-14T14:45:00+05:00")
        f = lambda *t: slots.freshness([{"published_at": x} for x in t], slot, now, common.parse_time)[0]
        self.assertTrue(f("2026-10-13T15:00:00+05:00"))                 # exactly 24 h
        self.assertFalse(f("2026-10-13T14:59:00+05:00"))
        self.assertTrue(f("2026-10-14T09:00:00+05:00", "2026-10-14T14:10:00+05:00"))   # newest decides
        self.assertFalse(f("2026-10-14T16:00:00+05:00"))                # future = wrong time zone
        self.assertTrue(f("2026-10-14T09:10:00Z"))                      # 14:10 PKT given in UTC
        upd = [{"published_at": "2026-10-13T08:00:00+05:00", "updated_at": "2026-10-14T14:00:00+05:00",
                "substantive_update": False}]
        self.assertFalse(slots.freshness(upd, slot, now, common.parse_time)[0])  # light refresh does not count
        upd[0]["substantive_update"] = True
        self.assertTrue(slots.freshness(upd, slot, now, common.parse_time)[0])


class Rules(unittest.TestCase):
    def setUp(self):
        os.environ["RISEUP_FAKE_NOW"] = "2026-10-14T14:45:00+05:00"
        import rules
        self.rules = rules

    def tearDown(self):
        os.environ.pop("RISEUP_FAKE_NOW", None)

    def test_valid_request(self):
        self.assertEqual(self.rules.validate(req(), "requests/2026-10-14-test-story.json"), [])

    def test_caption_rules(self):
        r = req(); r["caption"] = "Story text without the outlet name here at all. #RiseUpPakistan #a #b #c #d"
        self.assertTrue(any("source outlet" in e for e in self.rules.validate(r, "requests/2026-10-14-test-story.json")))
        r = req(); r["caption"] = "Story text, says Dawn. More text here for length.\n\n#RiseUpPakistan #a #b"
        self.assertTrue(any("exactly 5" in e for e in self.rules.validate(r, "requests/2026-10-14-test-story.json")))

    def test_wrong_card_date_rejected(self):
        r = req(); r["card"]["date"] = "15 OCT 2026"
        self.assertTrue(any("card.date" in e for e in self.rules.validate(r, "requests/2026-10-14-test-story.json")))

    def test_missing_offset_rejected(self):
        r = req(); r["sources"][0]["published_at"] = "2026-10-14T14:20:00"
        self.assertTrue(any("WITH offset" in e for e in self.rules.validate(r, "requests/2026-10-14-test-story.json")))

    def test_slot_must_be_whole_hour(self):
        r = req(); r["publish"]["slot"] = "2026-10-14T15:30:00+05:00"
        self.assertTrue(any("publish.slot" in e for e in self.rules.validate(r, "requests/2026-10-14-test-story.json")))
        r["publish"]["slot"] = "2026-10-15T01:00:00+05:00"
        self.assertTrue(any("publish.slot" in e for e in self.rules.validate(r, "requests/2026-10-14-test-story.json")))

    def test_stale_rejected(self):
        r = req(); r["sources"] = [{"outlet": "Dawn", "url": "https://www.dawn.com/news/1",
                                    "published_at": "2026-10-13T11:00:00+05:00"},
                                   {"outlet": "Geo", "url": "https://www.geo.tv/2", "published_at": "2026-10-13T12:30:00+05:00"}]
        with self.assertRaises(self.rules.Reject):
            self.rules.freshness(r, P("2026-10-14T15:00:00+05:00"))

    def test_entry_day_midnight(self):
        self.assertEqual(common.entry_day({"scheduled": "2026-10-15 00:00 PKT"}), "2026-10-14")
        self.assertEqual(common.entry_day({"scheduled": "2026-10-14 13:04 PKT"}), "2026-10-14")


class Payloads(unittest.TestCase):
    def test_feed_and_story(self):
        media = {"feed": "https://raw.githubusercontent.com/x/y/main/posts/a.jpg",
                 "story": "https://raw.githubusercontent.com/x/y/main/posts/a-story.jpg", "reel_kind": "none"}
        out, uses_tt = payloads.build(req(), media, P("2026-10-14T15:00:00+05:00"), True)
        feed, story = out["feed"], out["story"]
        self.assertEqual([p["network"] for p in feed["providers"]], ["facebook", "instagram", "tiktok"])
        self.assertEqual(feed["tiktokData"]["privacyOption"], "PUBLIC_TO_EVERYONE")
        self.assertTrue(feed["tiktokData"]["autoAddMusic"])
        self.assertNotIn("isAigc", feed["tiktokData"])          # not supported on photo posts
        self.assertEqual(feed["publicationDate"], {"dateTime": "2026-10-14T15:00:00", "timezone": "Asia/Karachi"})
        self.assertEqual(story["publicationDate"]["dateTime"], "2026-10-14T15:05:00")
        self.assertEqual(story["facebookData"]["type"], "STORY")
        self.assertEqual(story["instagramData"]["type"], "STORY")
        self.assertNotIn("text", story)
        self.assertTrue(uses_tt)

    def test_tiktok_cap_drops_tiktok(self):
        media = {"feed": "f", "story": "s", "reel_kind": "none"}
        out, uses_tt = payloads.build(req(), media, P("2026-10-14T15:00:00+05:00"), False)
        self.assertNotIn("tiktok", [p["network"] for p in out["feed"]["providers"]])
        self.assertNotIn("tiktokData", out["feed"])
        self.assertFalse(uses_tt)

    def test_midnight_story_rolls_to_next_date(self):
        media = {"feed": "f", "story": "s", "reel_kind": "none"}
        out, _ = payloads.build(req(), media, P("2026-10-15T00:00:00+05:00"), True)
        self.assertEqual(out["feed"]["publicationDate"]["dateTime"], "2026-10-15T00:00:00")
        self.assertEqual(out["story"]["publicationDate"]["dateTime"], "2026-10-15T00:05:00")


if __name__ == "__main__":
    unittest.main()
