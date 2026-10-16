# Changelog

All notable changes are documented here. Format: [Keep a Changelog](https://keepachangelog.com/), versioning: [SemVer](https://semver.org/).

## [0.2.0] - 2026-10-16
### Changed
- **Python 3.10+ is now required** (`requires-python = ">=3.10"`); Python 3.9 is end-of-life and is no longer supported. CI tests Python 3.10 and 3.12, and ruff targets `py310`.
- Docker image base bumped from `python:3.12-slim` to `python:3.14-slim`.
- Dev dependencies: `pytest>=9.1.1` (was `>=7`), `ruff>=0.17.0` (was `>=0.1`).
- README: Korean summary at the top, a License badge, and a License section that links `SECURITY.md`.
- CI actions bumped: `actions/checkout` 4 → 7, `actions/setup-python` 5 → 7, `dependabot/fetch-metadata` 2 → 3.

### Added
- Dependabot weekly updates for pip, GitHub Actions and the Docker base image, with auto-merge of patch/minor updates once checks pass.

## [0.1.0] - 2026-06-17
### Added
- Initial public release.
