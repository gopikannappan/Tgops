# Changelog

All notable changes to TGOps are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Phase 5: REST API (FastAPI) — in progress

## [0.1.0] — 2026-03-10

Initial open source release (Phases 0–4).

### Added
- `tgops account setup / status / verify` — OTP wizard and session management
- `tgops group list / inspect / snapshot` — read-only group intelligence
- `tgops migrate plan / run / resume / status / batch` — 10-step resumable group migration engine
- `tgops admin list / add / remove / export / sync` — admin roster lifecycle
- `tgops invite rotate / status` — invite link management
- `tgops member find / offboard / emergency / ban / status` — cross-group member offboarding
- Hydrogram MTProto client with FloodWait retry loop and Gaussian jitter delays
- Append-only JSONL audit log at `~/.tgops/audit.jsonl`
- JSON-file job state persistence with resume-at-any-step support
- Emergency offboarding mode with automatic invite link rotation across all managed groups
- Webhook alert dispatcher (Telegram bot + Slack)
- Docker and docker-compose support
- GitHub Actions CI
