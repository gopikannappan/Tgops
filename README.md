# TGOps

![Version](https://img.shields.io/badge/version-v0.1.0-blue)
![CI](https://github.com/[org]/tgops/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-green)

Self-hostable Telegram community ops toolkit — group migration, admin lifecycle, and member offboarding via MTProto.

---

## The Problem

Telegram has no workspace primitive. Every group is owned by a personal phone number. When that person leaves, the group is orphaned with no recovery path.

The Bot API cannot transfer group ownership — MTProto can. TGOps uses MTProto directly (via [Hydrogram](https://github.com/hydrogram/hydrogram)) to perform operations that are simply impossible with a bot token.

---

## What TGOps Does

- **Group migration** — 10-step, resumable migration engine with state persistence
- **Ownership transfer** — transfer group ownership from any account to the org account via MTProto
- **Admin roster sync** — export, import, and diff admin rosters across groups
- **Cross-group member offboarding** — planned and emergency modes (see below)
- **Invite link rotation** — revoke and regenerate invite links across all managed groups
- **Audit trail** — append-only JSONL log of every action taken

---

## Warning: ToS Disclaimer

> TGOps operates in a grey area of Telegram's Terms of Service. It automates a user account you own and control. Telegram may restrict accounts it detects as automated. You deploy at your own discretion.

This is the same posture taken by Dragon-Userbot, Kurimuzon-Userbot, and the broader Pyrogram/Hydrogram ecosystem. Use a dedicated account, not your personal number.

---

## Prerequisites

- A dedicated Telegram account for the org (the "org account") — not your personal number
- Telegram API credentials from [my.telegram.org](https://my.telegram.org)
- A dedicated phone number (see [Choosing a Phone Number](#choosing-a-phone-number) below)
- Python 3.11+ or Docker

---

## Quick Start (Docker — recommended)

```bash
# 1. Copy env file and add credentials
cp .env.example .env

# 2. First-time auth
docker compose run --rm tgops account setup

# 3. Check account status
docker compose run --rm tgops account status

# 4. List groups
docker compose run --rm tgops group list
```

---

## Quick Start (Local)

```bash
git clone https://github.com/[org]/tgops
cd tgops
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env  # fill in credentials
tgops account setup
```

---

## Configuration

Two methods are supported. Environment variables always take precedence over `tgops.yaml`.

### Environment Variables (required)

| Variable | Description |
|---|---|
| `TGOPS_API_ID` | Telegram API app ID (from my.telegram.org) |
| `TGOPS_API_HASH` | Telegram API app hash |
| `TGOPS_PHONE` | Org account phone number |

### Optional Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TGOPS_DRY_RUN` | `false` | Skip all destructive API calls |
| `TGOPS_WEBHOOK_URL` | `` | Alert webhook URL |
| `TGOPS_SESSION_PATH` | `~/.tgops/sessions/org_account` | Session file path |

Use `tgops.yaml` for full configuration — see `.env.example` for all available options. Environment variables always override file-based config.

---

## Commands Reference

### Account

| Command | Description |
|---|---|
| `tgops account setup` | Interactive OTP wizard — authenticate the org account |
| `tgops account status` | Show account info, session path, group count |
| `tgops account verify` | Confirm the session is valid and authorized |

### Group

| Command | Description |
|---|---|
| `tgops group list` | List all groups the org account belongs to |
| `tgops group inspect GROUP_ID` | Show detailed info about a specific group |
| `tgops group snapshot GROUP_ID` | Capture a full group state snapshot to JSON |

### Migrate

| Command | Description |
|---|---|
| `tgops migrate plan GROUP_ID` | Preview the 10-step migration plan (no API calls) |
| `tgops migrate run GROUP_ID` | Execute a full group migration |
| `tgops migrate status JOB_ID` | Show the status of a migration job |
| `tgops migrate resume JOB_ID` | Resume a failed or interrupted migration |
| `tgops migrate batch --file FILE` | Sequential migration of multiple groups from a file |

### Admin

| Command | Description |
|---|---|
| `tgops admin list GROUP_ID` | List all admins in a group |
| `tgops admin add GROUP_ID USER_ID` | Promote a user to admin |
| `tgops admin remove GROUP_ID USER_ID` | Demote an admin to regular member |
| `tgops admin export GROUP_ID` | Export admin roster to CSV |
| `tgops admin sync GROUP_ID --roster FILE` | Sync admin roster from a CSV file |

### Invite

| Command | Description |
|---|---|
| `tgops invite rotate GROUP_ID` | Revoke the current invite link and generate a new one |
| `tgops invite status GROUP_ID` | Show current invite link info |

### Member

| Command | Description |
|---|---|
| `tgops member find USER_ID` | Scan all groups and show user membership status |
| `tgops member offboard USER_ID` | Remove user from all managed groups (planned mode) |
| `tgops member emergency USER_ID` | Emergency removal with minimal delays + rotate all invite links |
| `tgops member ban USER_ID` | Ban user from specified groups or all managed groups |
| `tgops member status JOB_ID` | Show status of an offboarding job |

---

## Migration Walkthrough

### 1. Plan

```bash
tgops migrate plan 1234567890
```

Outputs the 10-step plan without making any API calls. Use this to review before committing.

### 2. Run

```bash
tgops migrate run 1234567890 --new-title "Acme Engineering"
```

The 10-step migration engine:

1. Snapshot source group state
2. Create new supergroup
3. Update title, description, and username
4. Transfer ownership (requires 24h membership — see note below)
5. Copy pinned messages
6. Sync admin roster from source
7. Export and re-import invite links
8. Send redirect notice in source group
9. Archive source group
10. Write final audit entry

Migration state is persisted to `~/.tgops/jobs/<job_id>.json` after every step. If interrupted, resume from the last completed step.

### 3. Resume

```bash
tgops migrate resume <job_id>
```

### Note on Ownership Transfer

Telegram requires the org account to have been a member of the source group for at least **24 hours** before ownership can be transferred. Plan accordingly.

---

## Member Offboarding

### Planned Mode

```bash
tgops member offboard 123456789 --message "Your access has been revoked."
```

Removes the user from all managed groups with Gaussian-jittered delays between API calls to stay under flood limits. Sends an optional message first.

### Emergency Mode

```bash
tgops member emergency 123456789
```

Removes the user with minimal delays across all managed groups, then immediately rotates all invite links. Use when a compromised account needs to be locked out quickly. High flood risk — Telegram may temporarily rate-limit the org account.

---

## Choosing a Phone Number

The org account phone number is permanent infrastructure. Choose carefully.

| Option | Notes |
|---|---|
| **Fragment** (fragment.com) | Blockchain Telegram numbers. Ideal for Web3 orgs. ~$10–50 at auction. Requires a TON wallet. Numbers are fully transferable. |
| **HeroSMS** (herosms.com) | OTP numbers for test and setup accounts. SMS-Activate shut down December 2025 — HeroSMS is the official successor. |
| **5SIM** (5sim.net) | 195 countries, API-friendly. Good alternative to HeroSMS for automation. |
| **Real SIM / eSIM** | Recommended for the long-term org account. Telegram's 2026 spam filters now actively reject many VoIP-category numbers. |

Never use free, temporary, or publicly-shared numbers. They fail registration or get silently restricted within hours.

---

## State and Audit Logs

- **Job state**: `~/.tgops/jobs/<job_id>.json` — written after every step, resumable at any point
- **Audit log**: `~/.tgops/audit.jsonl` — append-only JSONL, one entry per action

Example audit entry:

```json
{"ts": "2026-03-10T12:00:00Z", "event": "group.snapshot", "group_id": 1234567890, "details": {...}}
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run `pytest tests/unit/` before submitting
4. Open a pull request

Pre-commit hooks are configured in `.pre-commit-config.yaml`. Install with `pre-commit install`.

---

## License

MIT — see [LICENSE](LICENSE).
