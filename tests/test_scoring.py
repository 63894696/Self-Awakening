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

    def test_choice_conclusion_beats_first_mention(self):
        answer = (
            "**逐项分析：**\n\n- **A. 它会漂浮** — 不能必然成立\n"
            "- **B. 它很轻** — 必然成立\n\n## 答案\n\n**B**"
        )
        self.assertEqual(extract_choice(answer), "B")

    def test_trailing_bold_letter_is_used(self):
        self.assertEqual(extract_choice("百位 = 5\n\n**C**"), "C")

    def test_numeric_uses_last_number_not_first(self):
        score, _ = score_answer("126", "100 减去 37 再乘以 2：(100 - 37) × 2 = 63 × 2 = **126**")
        self.assertEqual(score, 1.0)

    def test_numeric_wrong_conclusion_is_a_failure(self):
        score, _ = score_answer("126", "126 * 2 = 252")
        self.assertEqual(score, 0.0)


if __name__ == "__main__":
    unittest.main()

