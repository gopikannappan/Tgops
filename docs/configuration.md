# Configuration

TGOps reads configuration from three sources, in order of increasing priority:

1. `tgops.yaml` / `tgops.yml` / `~/.tgops/tgops.yaml`
2. `.env` file in the current directory
3. Environment variables (always win)

---

## Environment Variables

All env vars are prefixed with `TGOPS_`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `TGOPS_API_ID` | Yes | — | Telegram API ID from my.telegram.org |
| `TGOPS_API_HASH` | Yes | — | Telegram API hash from my.telegram.org |
| `TGOPS_PHONE` | Yes | — | Phone number in international format (e.g. `+15551234567`) |
| `TGOPS_SESSION_PATH` | No | `~/.tgops/sessions/org_account` | Path to the Hydrogram session file |
| `TGOPS_AUDIT_LOG_PATH` | No | `~/.tgops/audit.jsonl` | Path to the append-only audit log |
| `TGOPS_JOBS_DIR` | No | `~/.tgops/jobs` | Directory for migration job JSON files |
| `TGOPS_OFFBOARDING_DIR` | No | `~/.tgops/offboarding` | Directory for offboarding job JSON files |
| `TGOPS_BASE_DELAY_SECONDS` | No | `2.5` | Base delay between API calls (seconds) |
| `TGOPS_MAX_FLOOD_RETRIES` | No | `3` | Maximum FloodWait retry attempts |
| `TGOPS_EMERGENCY_DELAY_SECONDS` | No | `1.0` | Minimal delay for emergency operations |
| `TGOPS_DRY_RUN` | No | `false` | If `true`, skip all destructive API calls |
| `TGOPS_WEBHOOK_URL` | No | `""` | URL for webhook alerts (Telegram bot or Slack) |
| `TGOPS_WEBHOOK_TYPE` | No | `telegram` | Webhook type: `telegram` or `slack` |
| `TGOPS_API_KEY` | No | `""` | REST API bearer token. Empty = no auth (local use only) |
| `TGOPS_EMERGENCY_ROTATE_INVITES` | No | `true` | Rotate all invite links after emergency offboarding |
| `TGOPS_DEFAULT_OFFBOARD_MESSAGE` | No | `""` | Default message sent to offboarded members |
| `TGOPS_ARCHIVE_MESSAGE` | No | `"This group has been archived.\nPlease join our new group: {invite_link}"` | Message pinned in archived groups (`{invite_link}` is replaced) |
| `TGOPS_ARCHIVE_PREFIX` | No | `[ARCHIVED]` | Prefix added to archived group titles |
| `TGOPS_REDIRECT_INTERVAL_SECONDS` | No | `3600` | How often (seconds) the redirect handler fires |

---

## tgops.yaml Reference

```yaml
# Telegram credentials (can use env vars instead)
api_id: 12345678
api_hash: "your_api_hash_here"
phone: "+15551234567"

# Paths
session_path: "~/.tgops/sessions/org_account"
audit_log_path: "~/.tgops/audit.jsonl"
jobs_dir: "~/.tgops/jobs"
offboarding_dir: "~/.tgops/offboarding"

# Rate limiting
base_delay_seconds: 2.5
max_flood_retries: 3
emergency_delay_seconds: 1.0

# Feature flags
dry_run: false

# REST API
api_key: ""  # Leave empty for local-only use

# Webhook alerts
webhook_url: ""
webhook_type: "telegram"  # or "slack"

# Emergency behaviour
emergency_rotate_invites: true

# Message templates
default_offboard_message: ""
archive_message: "This group has been archived.\nPlease join our new group: {invite_link}"
archive_prefix: "[ARCHIVED]"
redirect_interval_seconds: 3600
```

---

## .env File Example

```dotenv
TGOPS_API_ID=12345678
TGOPS_API_HASH=your_api_hash_here
TGOPS_PHONE=+15551234567
TGOPS_API_KEY=mysecretapikey
TGOPS_WEBHOOK_URL=https://api.telegram.org/bot<token>/sendMessage
TGOPS_WEBHOOK_TYPE=telegram
```
