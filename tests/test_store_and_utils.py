"""Tests for the persistent store and the safe calculator."""

import ast
import tempfile
import unittest
from pathlib import Path

from salaam.config import config
from salaam.tools.utils import _evaluate


def evaluate(expression):
    return _evaluate(ast.parse(expression, mode="eval"))


class StoreTests(unittest.TestCase):
    def setUp(self):
        # Point the store at a throwaway directory so tests never touch ~/.salaam
        self._original = config.DATA_DIR
        self._temp = tempfile.TemporaryDirectory()
        config.DATA_DIR = Path(self._temp.name)

    def tearDown(self):
        config.DATA_DIR = self._original
        self._temp.cleanup()

    def test_missing_collection_reads_as_empty(self):
        from salaam import store

        self.assertEqual(store.load("nothing"), [])

    def test_append_assigns_incrementing_ids(self):
        from salaam import store

        first = store.append("facts", {"fact": "a"})
        second = store.append("facts", {"fact": "b"})

        self.assertEqual(first["id"], 1)
        self.assertEqual(second["id"], 2)
        self.assertEqual(len(store.load("facts")), 2)
        self.assertIn("created_at", first)

    def test_remove_deletes_only_the_matching_row(self):
        from salaam import store

        store.append("facts", {"fact": "keep"})
        target = store.append("facts", {"fact": "drop"})

        removed = store.remove("facts", target["id"])

        self.assertEqual(removed["fact"], "drop")
        self.assertEqual([row["fact"] for row in store.load("facts")], ["keep"])

    def test_remove_missing_id_returns_none(self):
        from salaam import store

        self.assertIsNone(store.remove("facts", 999))

    def test_update_patches_fields(self):
        from salaam import store

        row = store.append("reminders", {"text": "call mum", "done": False})
        updated = store.update("reminders", row["id"], done=True)

        self.assertTrue(updated["done"])
        self.assertTrue(store.load("reminders")[0]["done"])

    def test_corrupt_file_reads_as_empty_rather_than_crashing(self):
        from salaam import store

        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        (config.DATA_DIR / "facts.json").write_text("{not json", encoding="utf-8")

        self.assertEqual(store.load("facts"), [])

    def test_unicode_survives_a_round_trip(self):
        from salaam import store

        store.append("notes", {"title": "naira", "content": "₦1,550 — Ẹ káàbọ̀"})

        self.assertIn("₦", store.load("notes")[0]["content"])


class CalculatorTests(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(evaluate("2 + 3 * 4"), 14)
        self.assertEqual(evaluate("(2 + 3) * 4"), 20)
        self.assertEqual(evaluate("10 / 4"), 2.5)
        self.assertEqual(evaluate("-5 + 2"), -3)

    def test_allowed_functions_and_constants(self):
        self.assertEqual(evaluate("sqrt(16)"), 4)
        self.assertEqual(evaluate("max(3, 9)"), 9)
        self.assertAlmostEqual(evaluate("pi"), 3.14159, places=4)

    def test_rejects_arbitrary_code(self):
        for hostile in (
            "__import__('os').system('echo hi')",
            "open('secrets.txt').read()",
            "().__class__",
            "exit()",
        ):
            with self.subTest(hostile=hostile):
                with self.assertRaises(Exception):
                    evaluate(hostile)

    def test_rejects_huge_exponent(self):
        with self.assertRaises(ValueError):
            evaluate("9 ** 999999")

    def test_division_by_zero_raises(self):
        with self.assertRaises(ZeroDivisionError):
            evaluate("1/0")


if __name__ == "__main__":
    unittest.main()
