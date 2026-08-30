"""Offline tests for the news engine — no network required."""

import unittest
from datetime import datetime, timedelta, timezone

from salaam import news

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>Naira strengthens against the dollar - Nairametrics</title>
    <description>&lt;p&gt;The naira &lt;b&gt;gained&lt;/b&gt; ground today.&lt;/p&gt;</description>
    <link>https://example.com/naira</link>
    <pubDate>Wed, 29 Jul 2026 08:00:00 +0100</pubDate>
  </item>
  <item>
    <title>Naira Strengthens Against The Dollar</title>
    <description>Duplicate story from another outlet.</description>
    <link>https://other.com/naira</link>
    <pubDate>Wed, 29 Jul 2026 07:00:00 +0100</pubDate>
  </item>
  <item>
    <title>Completely different headline about Lagos traffic</title>
    <description>No date on this one.</description>
    <link>https://example.com/lagos</link>
  </item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Atom style headline</title>
    <link href="https://atom.example/story"/>
    <summary>An atom summary.</summary>
    <updated>2026-07-29T06:00:00Z</updated>
  </entry>
</feed>"""


def parse(payload, source="Test"):
    root = news.net.parse_xml(payload)
    entries = root.findall(".//item") or root.findall(f".//{news.ATOM}entry")
    return [news._normalise(entry, source) for entry in entries]


class FeedParsingTests(unittest.TestCase):
    def test_parses_rss_and_strips_html(self):
        articles = parse(RSS)

        self.assertEqual(len(articles), 3)
        self.assertEqual(articles[0]["summary"], "The naira gained ground today.")
        self.assertEqual(articles[0]["link"], "https://example.com/naira")

    def test_parses_atom_link_href(self):
        articles = parse(ATOM)

        self.assertEqual(articles[0]["title"], "Atom style headline")
        self.assertEqual(articles[0]["link"], "https://atom.example/story")

    def test_google_news_title_splits_out_publisher(self):
        articles = parse(RSS, source="Google News")

        self.assertEqual(articles[0]["title"], "Naira strengthens against the dollar")
        self.assertEqual(articles[0]["source"], "Nairametrics")

    def test_non_google_source_keeps_full_title(self):
        articles = parse(RSS, source="Punch")

        self.assertIn(" - Nairametrics", articles[0]["title"])
        self.assertEqual(articles[0]["source"], "Punch")

    def test_strips_publisher_boilerplate_from_summary(self):
        for junk in (
            "Real summary here. Read More: https://punchng.com/story/",
            "Real summary here. The post Something appeared first on Punch.",
            "Real summary here. Continue reading at our site",
            "Real summary here. https://example.com/tracking?utm=1",
        ):
            with self.subTest(junk=junk):
                self.assertEqual(news._clean_summary(junk), "Real summary here.")

    def test_strips_hacker_news_metadata_entirely(self):
        raw = "Article URL: https://x.com/a Comments URL: https://y.com/b Points: 10 # Comments: 4"

        self.assertEqual(news._clean_summary(raw), "")

    def test_summary_truncates_on_a_word_boundary(self):
        summary = news._clean_summary("alpha bravo charlie delta echo", limit=14)

        self.assertEqual(summary, "alpha bravo…")

    def test_malformed_xml_returns_none_rather_than_raising(self):
        self.assertIsNone(news.net.parse_xml("<rss><unclosed>"))

    def test_missing_title_entry_is_dropped(self):
        root = news.net.parse_xml("<rss><channel><item><link>x</link></item></channel></rss>")
        self.assertIsNone(news._normalise(root.find(".//item"), "Test"))


class RankingTests(unittest.TestCase):
    def test_dedupe_collapses_same_story_from_two_outlets(self):
        # Google News strips the "- Publisher" suffix, so the same story
        # reported twice fingerprints identically and collapses to one.
        unique = news.dedupe(parse(RSS, source="Google News"))

        self.assertEqual([article["title"] for article in unique], [
            "Naira strengthens against the dollar",
            "Completely different headline about Lagos traffic",
        ])

    def test_dedupe_is_case_and_punctuation_insensitive(self):
        articles = [
            {"title": "Naira strengthens against the dollar"},
            {"title": "NAIRA STRENGTHENS, AGAINST THE DOLLAR!"},
        ]

        self.assertEqual(len(news.dedupe(articles)), 1)

    def test_sort_recent_puts_newest_first_and_undated_last(self):
        ordered = news.sort_recent(parse(RSS))

        self.assertEqual(ordered[0]["link"], "https://example.com/naira")
        self.assertIsNone(ordered[-1]["published_at"])

    def test_curate_applies_limit(self):
        self.assertEqual(len(news.curate(parse(RSS), 1)), 1)

    def test_diversify_spreads_across_outlets(self):
        # Punch publishes far more often; without a spread it fills every slot.
        articles = [{"source": "Punch", "title": f"punch {i}"} for i in range(10)]
        articles += [
            {"source": "Channels", "title": "channels one"},
            {"source": "The Cable", "title": "cable one"},
        ]

        sources = [a["source"] for a in news.diversify(articles, 3)]

        self.assertEqual(sorted(sources), ["Channels", "Punch", "The Cable"])

    def test_diversify_backfills_when_outlets_run_out(self):
        articles = [{"source": "Punch", "title": f"p{i}"} for i in range(5)]
        articles.append({"source": "Channels", "title": "c1"})

        picked = news.diversify(articles, 4)

        self.assertEqual(len(picked), 4)
        self.assertEqual(sum(a["source"] == "Punch" for a in picked), 3)

    def test_curate_keeps_newest_first_after_diversifying(self):
        ordered = news.curate(parse(RSS, source="Google News"), 5)
        stamps = [a["published_at"] for a in ordered if a["published_at"]]

        self.assertEqual(stamps, sorted(stamps, reverse=True))


class FormattingTests(unittest.TestCase):
    def test_render_returns_fallback_when_empty(self):
        self.assertEqual(news.render("X", [], "nothing here"), "nothing here")

    def test_render_includes_titles_and_sources(self):
        output = news.render("HEADLINES", news.curate(parse(RSS, "Punch"), 5), "")

        self.assertIn("HEADLINES", output)
        self.assertIn("Lagos traffic", output)
        self.assertIn("Punch", output)

    def test_ago_formats_relative_ages(self):
        now = datetime.now(timezone.utc)

        self.assertEqual(news._ago(None), "")
        self.assertIn("m ago", news._ago(now - timedelta(minutes=30)))
        self.assertIn("h ago", news._ago(now - timedelta(hours=5)))
        self.assertIn("d ago", news._ago(now - timedelta(days=2)))


def story(source, title, hours_ago=1, summary=""):
    return {
        "source": source,
        "title": title,
        "summary": summary,
        "link": "https://x.test/a",
        "published": "",
        "published_at": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
    }


class SignificanceTests(unittest.TestCase):
    def test_widely_covered_story_outranks_a_newer_lone_one(self):
        articles = [
            story("Blog", "Local footballer signs boot sponsorship deal", hours_ago=0),
            story("Punch", "Central bank raises interest rate to 27 percent", 5),
            story("Vanguard", "CBN raises interest rate amid inflation", 5),
            story("Channels", "Central bank raises benchmark interest rate", 5),
        ]

        ranked = news.rank_by_significance(articles, 5)

        self.assertIn("interest rate", ranked[0]["title"].lower())
        self.assertEqual(ranked[0]["outlet_count"], 3)

    def test_reworded_headlines_group_into_one_story(self):
        articles = [
            story("A", "Saudi Arabia joins US in strikes on Iran-backed militias"),
            story("B", "US and Saudi forces strike Iran-backed militias in Iraq"),
        ]

        ranked = news.rank_by_significance(articles, 5)

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["outlet_count"], 2)

    def test_unrelated_stories_are_not_merged(self):
        articles = [
            story("A", "Central bank raises interest rate sharply"),
            story("B", "Super Eagles defeat Ghana in Abuja friendly"),
        ]

        self.assertEqual(len(news.rank_by_significance(articles, 5)), 2)

    def test_stories_outside_the_window_are_excluded(self):
        articles = [
            story("A", "Something significant happened yesterday", hours_ago=40),
            story("B", "Something significant happened yesterday", hours_ago=40),
            story("C", "Fresh development reported this morning", hours_ago=2),
        ]

        ranked = news.rank_by_significance(articles, 5, within_hours=24)

        self.assertEqual(len(ranked), 1)
        self.assertIn("Fresh development", ranked[0]["title"])

    def test_cluster_keeps_the_version_that_has_a_summary(self):
        articles = [
            story("A", "Central bank raises interest rate", 3),
            story("B", "Central bank raises interest rate", 2, summary="Full detail here."),
        ]

        ranked = news.rank_by_significance(articles, 5)

        self.assertEqual(ranked[0]["summary"], "Full detail here.")

    def test_render_reports_how_many_outlets_carry_it(self):
        ranked = news.rank_by_significance(
            [story("A", "Central bank raises rate"), story("B", "Central bank raises rate")], 3
        )
        output = news.render_significant("TOP", ranked, "")

        self.assertIn("2 outlets covering", output)
        self.assertIn("Reported by:", output)


TRENDS_RSS = """<?xml version="1.0"?>
<rss xmlns:ht="https://trends.google.com/trending/rss" version="2.0"><channel>
 <item>
  <title>dollar</title>
  <ht:approx_traffic>200+</ht:approx_traffic>
  <ht:news_item>
    <ht:news_item_title>Dollar slips as Fed holds rates steady</ht:news_item_title>
    <ht:news_item_source>Reuters</ht:news_item_source>
    <ht:news_item_url>https://reuters.test/a</ht:news_item_url>
  </ht:news_item>
 </item>
 <item><title>bare term</title></item>
</channel></rss>"""


class TrendsTests(unittest.TestCase):
    def test_parses_term_traffic_and_explaining_headlines(self):
        trends = news.parse_trends(TRENDS_RSS)

        self.assertEqual(trends[0]["term"], "dollar")
        self.assertEqual(trends[0]["traffic"], "200+")
        self.assertEqual(trends[0]["stories"][0]["source"], "Reuters")
        self.assertIn("Fed holds rates", trends[0]["stories"][0]["title"])

    def test_term_without_news_items_still_parses(self):
        trends = news.parse_trends(TRENDS_RSS)

        self.assertEqual(trends[1]["term"], "bare term")
        self.assertEqual(trends[1]["stories"], [])

    def test_bad_payload_returns_empty(self):
        self.assertEqual(news.parse_trends(None), [])
        self.assertEqual(news.parse_trends("<rss><broken>"), [])


class UrlBuilderTests(unittest.TestCase):
    def test_search_url_encodes_query_and_window(self):
        url = news.google_news_search_url("fuel subsidy", "NG", 2)

        self.assertIn("fuel+subsidy", url)
        self.assertIn("when:2d", url)
        self.assertIn("gl=NG", url)

    def test_unknown_region_falls_back_to_nigeria(self):
        self.assertIn("gl=NG", news.google_news_search_url("x", "ATLANTIS"))

    def test_section_url_uses_topic(self):
        self.assertIn("topic/TECHNOLOGY", news.google_news_section_url("TECHNOLOGY", "US"))

    def test_top_url_is_the_front_page_not_a_section(self):
        url = news.google_news_top_url("NG")

        self.assertNotIn("topic/", url)
        self.assertIn("news.google.com/rss?", url)
        self.assertIn("gl=NG", url)


if __name__ == "__main__":
    unittest.main()
