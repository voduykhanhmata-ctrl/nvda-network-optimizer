# Contributing to NVDA Network Optimizer

[English](CONTRIBUTING.md) | [Tiếng Việt](CONTRIBUTING.vi.md)

Thank you for helping improve NVDA Network Optimizer. The project is authored by Võ Duy Khánh and welcomes respectful community contributions.

## Before you contribute

- Search existing issues before reporting a bug or proposing a feature.
- Describe the NVDA version, Windows version, network type, and steps to reproduce a problem. Do not post passwords, access tokens, public IP addresses, or other sensitive information.
- Test accessibility with NVDA. User-facing messages must be clear, concise, and usable with speech and braille.

## Code and documentation

- Keep all user-facing strings translatable with `_()`.
- English is the source language. Update `locale/vi/LC_MESSAGES/nvda.po` when changing a user-facing string, then run `python compile_translations.py` to regenerate `nvda.mo`.
- Keep both English and Vietnamese documentation accurate: `README.md`, `README.vi.md`, `doc/en/readme.html`, and `doc/vi/readme.html`.
- Do not add a free-form command field or execute user-supplied command text. Network-changing actions must be fixed, explained, confirmed, and safely elevated only when needed.

## Pull requests

1. Fork the repository and create a focused branch.
2. Make and test your change.
3. Explain what changed, why it is useful, and how you tested it.
4. Keep the pull request focused; use a separate pull request for unrelated changes.

By contributing, you agree that your contribution may be distributed under this project's [MIT License](LICENSE).
