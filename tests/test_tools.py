import unittest
from src.agent.tools import safe_math_eval, calc


class TestSafeMathEval(unittest.TestCase):
    """Unit tests for safe_math_eval AST mathematical parser."""

    def test_basic_arithmetic(self):
        self.assertEqual(safe_math_eval("2 + 2"), "4")
        self.assertEqual(safe_math_eval("10 - 4"), "6")
        self.assertEqual(safe_math_eval("3 * 7"), "21")
        self.assertEqual(safe_math_eval("20 / 4"), "5")

    def test_float_and_rounding(self):
        self.assertEqual(safe_math_eval("10 / 3"), "3.3333")
        self.assertEqual(safe_math_eval("2.5 * 4"), "10")

    def test_comma_as_decimal_separator(self):
        self.assertEqual(safe_math_eval("2,5 + 3,5"), "6")

    def test_parentheses_and_order_of_operations(self):
        self.assertEqual(safe_math_eval("(2 + 3) * 4"), "20")
        self.assertEqual(safe_math_eval("2 + 3 * 4"), "14")

    def test_division_by_zero(self):
        result = safe_math_eval("10 / 0")
        self.assertIn("zero", result.lower())

    def test_floor_division_by_zero(self):
        result = safe_math_eval("10 // 0")
        self.assertIn("zero", result.lower())

    def test_empty_or_whitespace(self):
        result = safe_math_eval("   ")
        self.assertIn("no evaluable", result.lower())

    def test_malicious_code_injection(self):
        # Expressions with Python builtins or system calls should be stripped or fail
        result = safe_math_eval("__import__('os').system('ls')")
        self.assertNotIn("0", result)
        # Should either filter out or produce calculation error
        self.assertTrue("error" in result.lower() or "no evaluable" in result.lower())

    def test_calc_tool_wrapper(self):
        res = calc.invoke({"expression": "100 * 1.2"})
        self.assertEqual(res, "120")


if __name__ == "__main__":
    unittest.main()
