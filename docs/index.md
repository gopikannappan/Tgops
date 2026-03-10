# TGOps

**Self-hostable Telegram community ops toolkit.**

Automate group migrations, member offboarding, admin roster management, and invite link rotation — all from a single CLI or REST API, running entirely on your own infrastructure.

---

## Features

- **Group Migration** — 10-step fully automated migration from one supergroup to another, with invite blast, redirect pinning, and audit trail.
- **Member Offboarding** — Remove a user from every managed group in planned or emergency mode. Rotates invite links automatically on emergency.
- **Admin Management** — List, add, remove, and sync admin rosters from CSV. Full privilege granularity.
- **Invite Rotation** — Revoke and regenerate invite links for one or all groups.
- **REST API** — Phase 5 FastAPI server for CI/CD pipelines, dashboards, and external integrations.
- **Audit Log** — Append-only JSONL audit trail for every destructive action.
- **Webhook Alerts** — Slack or Telegram bot notifications on key events.
- **Dry-run mode** — Simulate any operation without making real API calls.

---

## Quick Start

```bash
# 1. Install
pip install tgops

# 2. Configure
export TGOPS_API_ID=12345678
export TGOPS_API_HASH=your_api_hash
export TGOPS_PHONE=+15551234567

# 3. Authenticate
tgops account setup

# 4. Run a migration
tgops migrate run 1234567890

# 5. Start the REST API
tgops serve
```

---

## Links

- [Getting Started](getting-started.md)
- [Configuration Reference](configuration.md)
- [CLI Commands](commands.md)
- [REST API](api.md)
- [Commercial / Managed Migrations](commercial.md)
- [FAQ](faq.md)
