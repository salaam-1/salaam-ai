"""Offline tests for web-tool helpers."""

import unittest

from salaam.news import _restates
from salaam.tools.web import _strip, _unwrap


class UnwrapTests(unittest.TestCase):
    def test_unwraps_duckduckgo_redirect(self):
        wrapped = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fpunchng.com%2Fstory&rut=abc"

        self.assertEqual(_unwrap(wrapped), "https://punchng.com/story")

    def test_adds_scheme_to_protocol_relative_url(self):
        self.assertEqual(_unwrap("//example.com/x"), "https://example.com/x")

    def test_leaves_a_plain_url_alone(self):
        self.assertEqual(_unwrap("https://example.com/x"), "https://example.com/x")


class StripTests(unittest.TestCase):
    def test_removes_tags_and_unescapes_entities(self):
        self.assertEqual(_strip("<b>Caf&eacute;</b>  &amp; bar"), "Café & bar")


class RestatesTests(unittest.TestCase):
    def test_detects_summary_that_merely_repeats_the_title(self):
        title = "Naira slips against the dollar"

        self.assertTrue(_restates("Naira slips against the dollar", title))
        self.assertTrue(_restates("Naira slips against the dollar Business Post", title))

    def test_keeps_a_summary_that_adds_information(self):
        title = "Naira slips against the dollar"
        summary = (
            "The naira weakened to 1,550 per dollar at the official window on "
            "Tuesday as the central bank held rates steady amid pressure."
        )

        self.assertFalse(_restates(summary, title))

    def test_handles_empty_input(self):
        self.assertFalse(_restates("", "title"))
        self.assertFalse(_restates("summary", ""))


if __name__ == "__main__":
    unittest.main()
