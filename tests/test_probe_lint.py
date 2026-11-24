import unittest

from self_awaken.probe_lint import Issue, lint_probes, safe_eval_expected
from self_awaken.schemas import Probe


def probe(probe_id: str, prompt: str, expected, category: str = "code") -> Probe:
    return Probe(id=probe_id, category=category, prompt=prompt, expected=expected)


def codes(issues: list[Issue]) -> set[str]:
    return {issue.code for issue in issues}


class LintExpectedTests(unittest.TestCase):
    def test_placeholder_expected_is_error(self):
        issues = lint_probes([probe("p1", "compute", "<calc-failed>")])
        self.assertIn("placeholder_expected", codes(issues))

    def test_unevaluated_expression_is_error(self):
        issues = lint_probes([probe("p2", "sqrt of 5882", "int(5882 ** 0.5)")])
        self.assertIn("unevaluated_expected", codes(issues))

    def test_missing_expected_is_error(self):
        issues = lint_probes([probe("p3", "compute", "")])
        self.assertIn("missing_expected", codes(issues))

    def test_plain_number_is_fine(self):
        self.assertEqual(lint_probes([probe("p4", "compute", "42")]), [])

    def test_choice_probe_requires_letter(self):
        issues = lint_probes([probe("p5", "只选择 A、B、C 或 D。哪项正确？", "yes")])
        self.assertIn("choice_expected", codes(issues))

    def test_choice_probe_accepts_letter(self):
        self.assertEqual(lint_probes([probe("p6", "只选择 A、B、C 或 D。哪项正确？", "B")]), [])

    def test_arithmetic_mismatch_is_error(self):
        issues = lint_probes([probe("p7", "只输出数字：17 * 23 - 19 = ?", "999")])
        self.assertIn("arithmetic_mismatch", codes(issues))

    def test_correct_arithmetic_passes(self):
        self.assertEqual(lint_probes([probe("p8", "只输出数字：17 * 23 = ?", "391")]), [])


class LintPromptTests(unittest.TestCase):
    def test_unexpanded_field_is_error(self):
        issues = lint_probes([probe("p9", "计算 {a} + {b}", "3")])
        self.assertIn("unexpanded_field", codes(issues))

    def test_template_placeholder_prompt_is_error(self):
        issues = lint_probes([probe("p10", "计算 <a> + 1", "3")])
        self.assertIn("placeholder_prompt", codes(issues))

    def test_unexpanded_slot_is_warning(self):
        issues = lint_probes([probe("p11", "输出 OK/YES/TRUE 中的一项", "OK")])
        self.assertIn("unexpanded_slot", codes(issues))

    def test_duplicate_prompt_is_warning(self):
        issues = lint_probes([probe("p12", "same text", "1"), probe("p13", "same  text", "1")])
        self.assertIn("duplicate_prompt", codes(issues))

    def test_duplicate_id_is_error(self):
        issues = lint_probes([probe("p14", "a", "1"), probe("p14", "b", "2")])
        self.assertIn("duplicate_id", codes(issues))


class SafeEvalTests(unittest.TestCase):
    def test_evaluates_number_expression(self):
        self.assertEqual(safe_eval_expected("int(5882 ** 0.5)"), "76")

    def test_evaluates_string_expression(self):
        self.assertEqual(safe_eval_expected("str(1*3 + 5*5) + '/' + str(5*3)"), "28/15")

    def test_rejects_arbitrary_code(self):
        self.assertIsNone(safe_eval_expected("__import__('os').system('echo hi')"))
        self.assertIsNone(safe_eval_expected("open('x').read()"))


if __name__ == "__main__":
    unittest.main()
