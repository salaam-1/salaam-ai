"""Offline tests for the claim-verification engine."""

import unittest

from salaam import verify


def article(source, title, summary="", published=None):
    return {
        "source": source,
        "title": title,
        "summary": summary,
        "link": f"https://{source.lower().replace(' ', '')}.com/x",
        "published": "",
        "published_at": published,
    }


class SearchTermTests(unittest.TestCase):
    def test_strips_question_framing(self):
        terms = verify.search_terms(
            "Is it true that the government is banning cryptocurrency in Nigeria?"
        )

        self.assertNotIn("true", terms.lower().split())
        self.assertNotIn("that", terms.lower().split())
        for word in ("government", "banning", "cryptocurrency", "Nigeria"):
            self.assertIn(word, terms)

    def test_drops_hearsay_openers(self):
        terms = verify.search_terms("I heard the CBN really devalued the naira")

        self.assertNotIn("heard", terms.lower())
        self.assertNotIn("really", terms.lower())
        self.assertIn("CBN", terms)
        self.assertIn("naira", terms)

    def test_caps_length_but_keeps_proper_nouns(self):
        claim = (
            "Is it true that Dangote and Tinubu announced a massive new "
            "refinery expansion programme covering Lagos and Kano next year"
        )
        terms = verify.search_terms(claim, limit=5)

        self.assertLessEqual(len(terms.split()), 5)
        self.assertTrue({"Dangote", "Tinubu"} & set(terms.split()))

    def test_empty_claim_yields_no_terms(self):
        self.assertEqual(verify.search_terms("is it true?"), "")


class AssessmentTests(unittest.TestCase):
    def test_no_articles_is_no_coverage_not_false(self):
        result = verify.assess("something nobody reported", [])

        self.assertEqual(result["level"], "NO_COVERAGE")
        self.assertEqual(result["outlet_count"], 0)
        # The wording must not imply falsehood.
        text = verify.render(result, 14)
        self.assertIn("does NOT make it false", text)

    def test_many_outlets_one_headline_is_flagged_as_syndicated(self):
        # The dangerous case: twenty papers, one actual source.
        headline = "Government announces total ban on okada nationwide"
        articles = [
            article(f"Outlet {i}", headline) for i in range(8)
        ]

        result = verify.assess("okada banned nationwide", articles)

        self.assertTrue(result["syndicated"])
        self.assertEqual(result["level"], "SINGLE_SOURCE")
        self.assertIn("rumour", verify.render(result, 14))

    def test_independent_framings_across_outlets_reads_as_well_corroborated(self):
        articles = [
            article("Punch", "CBN raises interest rate to 27 percent"),
            article("Premium Times", "Central bank hikes benchmark rate amid inflation"),
            article("Channels TV", "MPC votes to increase lending rate again"),
            article("Reuters", "Nigeria tightens monetary policy as prices climb"),
        ]

        result = verify.assess("CBN raised interest rates", articles)

        self.assertEqual(result["level"], "WIDELY_REPORTED")
        self.assertFalse(result["syndicated"])
        self.assertEqual(result["outlet_count"], 4)

    def test_two_outlets_is_only_some_coverage(self):
        articles = [
            article("Punch", "Firm opens new plant in Ogun state"),
            article("Nairametrics", "Manufacturer commissions Ogun facility today"),
        ]

        result = verify.assess("new plant in Ogun", articles)

        self.assertEqual(result["level"], "SOME_COVERAGE")

    def test_render_always_warns_against_declaring_truth(self):
        articles = [article("Punch", "Something entirely ordinary happened today")]
        text = verify.render(verify.assess("something", articles), 7)

        self.assertIn("corroboration, not proof", text)

    def test_outlets_are_deduplicated_and_listed(self):
        articles = [
            article("Punch", "Alpha bravo charlie delta happened"),
            article("Punch", "Echo foxtrot golf hotel occurred"),
            article("Vanguard", "India juliett kilo lima reported"),
        ]

        result = verify.assess("x", articles)

        self.assertEqual(result["outlets"], ["Punch", "Vanguard"])


if __name__ == "__main__":
    unittest.main()
