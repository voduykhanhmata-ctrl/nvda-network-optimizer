# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Võ Duy Khánh

import configparser
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class ReleaseMetadataTests(unittest.TestCase):

	def test_manifest_identity_author_and_version_are_exact(self):
		manifest = (ROOT / "manifest.ini").read_text(encoding="utf-8-sig")
		parser = configparser.ConfigParser(interpolation=None)
		parser.read_string("[addon]\n" + manifest)
		self.assertEqual("networkOptimizer", parser["addon"]["name"])
		self.assertEqual('"Võ Duy Khánh"', parser["addon"]["author"])
		self.assertEqual("1.3.2", parser["addon"]["version"])

	def test_project_license_names_the_owner_and_gpl_identifier(self):
		license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
		self.assertTrue(license_text.startswith(
			"NVDA Network Optimizer\nCopyright (C) 2026 Võ Duy Khánh\n"
		))
		self.assertIn("SPDX-License-Identifier: GPL-2.0-or-later", license_text)
		self.assertIn("GNU GENERAL PUBLIC LICENSE", license_text)

	def test_source_and_build_files_name_the_same_owner(self):
		for relative_path in (
			"globalPlugins/networkOptimizer.py",
			"compile_translations.py",
			"build_addon.ps1",
		):
			with self.subTest(path=relative_path):
				text = (ROOT / relative_path).read_text(encoding="utf-8-sig")
				self.assertIn("SPDX-License-Identifier: GPL-2.0-or-later", text)
				self.assertIn("Copyright (C) 2026 Võ Duy Khánh", text)

	def test_build_reads_release_metadata_as_utf8(self):
		build_script = (ROOT / "build_addon.ps1").read_text(encoding="utf-8-sig")
		self.assertGreaterEqual(build_script.count("Get-Content -Raw -Encoding UTF8"), 2)
		self.assertIn("Get-Content -Encoding UTF8 -LiteralPath $manifestPath", build_script)

	def test_public_documentation_names_the_author(self):
		for relative_path in (
			"README.md", "README.vi.md",
			"doc/en/readme.html", "doc/vi/readme.html",
		):
			with self.subTest(path=relative_path):
				text = (ROOT / relative_path).read_text(encoding="utf-8")
				self.assertIn("Võ Duy Khánh", text)


if __name__ == "__main__":
	unittest.main()
