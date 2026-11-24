import unittest

from self_awaken.scoring import answer_digest, canonicalize, extract_choice, normalize_text, score_answer


class ScoringTests(unittest.TestCase):
    def test_normalize_text(self):
        self.assertEqual(normalize_text("  Hello\nWORLD  "), "hello world")

    def test_extract_choice(self):
        self.assertEqual(extract_choice("答案是 B。"), "B")
        self.assertIsNone(extract_choice("because this is not a choice"))

    def test_score_choice(self):
        score, choice = score_answer("B", "我选择 B")
        self.assertEqual(score, 1.0)
        self.assertEqual(choice, "B")

    def test_score_numeric_with_short_explanation(self):
        score, _ = score_answer("372", "372")
        self.assertEqual(score, 1.0)

    def test_digest_is_stable_after_whitespace_normalization(self):
        self.assertEqual(answer_digest("OK\n7"), answer_digest(" ok 7 "))

    def test_canonicalize_strips_markdown_and_quotes(self):
        self.assertEqual(canonicalize("```'ababab'```"), "ababab")
        self.assertEqual(canonicalize("`[0, 1, 2]`"), "[0,1,2]")
        self.assertEqual(canonicalize('"[1, 2, 3]"'), "[1,2,3]")

    def test_quoted_answer_is_not_a_failure(self):
        score, _ = score_answer("ababab", "'ababab'")
        self.assertEqual(score, 1.0)

    def test_backticked_list_is_not_a_failure(self):
        score, _ = score_answer("[0, 1, 2]", "`[0, 1, 2]`")
        self.assertEqual(score, 1.0)

    def test_different_list_is_a_failure(self):
        score, _ = score_answer("[0, 1, 2]", "[0, 1, 3]")
        self.assertEqual(score, 0.0)


if __name__ == "__main__":
    unittest.main()

