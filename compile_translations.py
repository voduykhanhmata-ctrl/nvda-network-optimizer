"""Compile gettext PO catalogs for the NVDA add-on without external tools."""

from __future__ import annotations

import ast
import struct
import sys
from pathlib import Path


def _quoted_value(value: str, source: Path, line_number: int) -> str:
	"""Read one gettext-quoted string with helpful errors."""
	try:
		parsed = ast.literal_eval(value)
	except (SyntaxError, ValueError) as error:
		raise ValueError(f"{source}:{line_number}: invalid PO string") from error
	if not isinstance(parsed, str):
		raise ValueError(f"{source}:{line_number}: expected a quoted PO string")
	return parsed


def read_catalog(source: Path) -> dict[str, str]:
	"""Read the simple, singular gettext catalog format used by this add-on."""
	entries: dict[str, str] = {}
	message_id: str | None = None
	message_text: str | None = None
	state: str | None = None

	def finish_entry() -> None:
		nonlocal message_id, message_text, state
		if message_id is None:
			return
		if message_text is None:
			raise ValueError(f"{source}: missing msgstr for {message_id!r}")
		if message_id in entries:
			raise ValueError(f"{source}: duplicate msgid {message_id!r}")
		entries[message_id] = message_text
		message_id = None
		message_text = None
		state = None

	for line_number, raw_line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
		line = raw_line.strip()
		if not line:
			finish_entry()
			continue
		if line.startswith("#"):
			continue
		if line.startswith("msgctxt ") or line.startswith("msgid_plural ") or line.startswith("msgstr["):
			raise ValueError(f"{source}:{line_number}: plural/context entries are not supported")
		if line.startswith("msgid "):
			finish_entry()
			message_id = _quoted_value(line[6:], source, line_number)
			state = "id"
			continue
		if line.startswith("msgstr "):
			if message_id is None:
				raise ValueError(f"{source}:{line_number}: msgstr appears before msgid")
			message_text = _quoted_value(line[7:], source, line_number)
			state = "str"
			continue
		if line.startswith('"'):
			if state == "id" and message_id is not None:
				message_id += _quoted_value(line, source, line_number)
				continue
			if state == "str" and message_text is not None:
				message_text += _quoted_value(line, source, line_number)
				continue
		raise ValueError(f"{source}:{line_number}: unsupported PO syntax")

	finish_entry()
	if "" not in entries:
		raise ValueError(f"{source}: missing gettext header")
	return entries


def compile_catalog(entries: dict[str, str]) -> bytes:
	"""Create a GNU MO binary catalog from a mapping of message IDs to texts."""
	message_ids = sorted(entries)
	originals = b"".join(message_id.encode("utf-8") + b"\0" for message_id in message_ids)
	translations = b"".join(entries[message_id].encode("utf-8") + b"\0" for message_id in message_ids)
	count = len(message_ids)
	original_table_offset = 7 * 4
	translation_table_offset = original_table_offset + count * 8
	originals_offset = translation_table_offset + count * 8
	translations_offset = originals_offset + len(originals)

	original_table: list[tuple[int, int]] = []
	translation_table: list[tuple[int, int]] = []
	original_offset = originals_offset
	translation_offset = translations_offset
	for message_id in message_ids:
		original = message_id.encode("utf-8")
		translation = entries[message_id].encode("utf-8")
		original_table.append((len(original), original_offset))
		translation_table.append((len(translation), translation_offset))
		original_offset += len(original) + 1
		translation_offset += len(translation) + 1

	header = struct.pack(
		"<7I",
		0x950412DE,
		0,
		count,
		original_table_offset,
		translation_table_offset,
		0,
		0,
	)
	original_index = b"".join(struct.pack("<2I", *entry) for entry in original_table)
	translation_index = b"".join(struct.pack("<2I", *entry) for entry in translation_table)
	return header + original_index + translation_index + originals + translations


def main() -> int:
	project_root = Path(__file__).resolve().parent
	sources = sorted((project_root / "locale").glob("*/LC_MESSAGES/nvda.po"))
	if not sources:
		raise FileNotFoundError("No locale/*/LC_MESSAGES/nvda.po files were found.")
	for source in sources:
		target = source.with_suffix(".mo")
		target.write_bytes(compile_catalog(read_catalog(source)))
		print(f"Compiled {source.relative_to(project_root)} -> {target.relative_to(project_root)}")
	return 0


if __name__ == "__main__":
	sys.exit(main())
