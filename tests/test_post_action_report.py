import ast
import unittest
from pathlib import Path


SOURCE_PATH = Path(__file__).parents[1] / "globalPlugins" / "networkOptimizer.py"


def load_report_function(run_process):
	"""Load the two pure report helpers without importing NVDA or wxPython."""
	tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8-sig"), filename=str(SOURCE_PATH))
	helpers = [
		node
		for node in tree.body
		if isinstance(node, ast.FunctionDef) and node.name in {"_trim_output", "_post_action_report"}
	]
	namespace = {
		"_": lambda message: message,
		"_run_process": run_process,
		"PROVIDER_BY_ID": {"cloudflare": ("Cloudflare", ("1.1.1.1", "1.0.0.1"))},
	}
	exec(compile(ast.Module(body=helpers, type_ignores=[]), str(SOURCE_PATH), "exec"), namespace)
	return namespace["_post_action_report"]


class PostActionReportTests(unittest.TestCase):
	adapter = {"index": 7, "alias": "Wi-Fi"}

	def test_apply_dns_reports_success_after_readback(self):
		report_function = load_report_function(lambda _argv, timeout=0: (0, "DNS Servers: 1.1.1.1"))
		report, succeeded = report_function("applyDns", "cloudflare", self.adapter, 0, None)
		self.assertIs(succeeded, True)
		self.assertIn("Configuration read back:", report)

	def test_apply_dns_readback_failure_is_unverified(self):
		report_function = load_report_function(lambda _argv, timeout=0: (-1, "netsh failed"))
		report, succeeded = report_function("applyDns", "cloudflare", self.adapter, 0, None)
		self.assertIsNone(succeeded)
		self.assertIn("read-back code -1", report)

	def test_restore_dns_empty_readback_is_unverified(self):
		report_function = load_report_function(lambda _argv, timeout=0: (0, ""))
		report, succeeded = report_function("restoreDhcpDns", None, self.adapter, 0, None)
		self.assertIsNone(succeeded)
		self.assertIn("read-back code 0", report)

	def test_failed_elevated_command_does_not_attempt_readback(self):
		def unexpected_readback(_argv, timeout=0):
			raise AssertionError("readback should not run")

		report_function = load_report_function(unexpected_readback)
		_report, succeeded = report_function("applyDns", "cloudflare", self.adapter, 1, None)
		self.assertIs(succeeded, False)


if __name__ == "__main__":
	unittest.main()
