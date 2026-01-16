import os
import sys
import unittest

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.review_engine import ReviewEngine


class TestReviewEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ReviewEngine()

    def test_analyze_code_syntax_error(self):
        code = "def invalid_syntax("
        issues = self.engine.analyze_code(code)
        self.assertTrue(any("CRITICAL: Syntax Error" in issue for issue in issues))

    def test_analyze_code_lint_issues(self):
        # Code with unused import and missing whitespace
        code = "import os\ndef func(a,b):\n    return a+b"
        issues = self.engine.analyze_code(code)

        # If pylint is not installed, we should see the warning message
        if any("pylint not found" in issue for issue in issues):
            self.assertTrue(True)  # Skip check if pylint missing
        else:
            # Pylint uses different codes. W0611 is unused import.
            # We just check if there are LINT issues found.
            self.assertTrue(any("LINT:" in issue for issue in issues))

    def test_scan_security_risks(self):
        code = "api_key = 'AKIA1234567890ABCDEF'\nos.system('rm -rf /')"
        risks = self.engine.scan_security(code)
        self.assertTrue(any("AWS Key" in risk for risk in risks))
        self.assertTrue(any("Dangerous System Call" in risk for risk in risks))

    def test_generate_diff_html(self):
        old = "line1\nline2"
        new = "line1\nline2_modified"
        html = self.engine.generate_diff_html(old, new)
        self.assertIn("<pre", html)
        self.assertIn("line2_modified", html)


if __name__ == "__main__":
    unittest.main()
