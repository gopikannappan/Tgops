# Getting Started

## Prerequisites

- Python 3.11+ **or** Docker
- A Telegram account (real SIM or virtual number — see [FAQ](faq.md))
- Telegram API credentials from [my.telegram.org](https://my.telegram.org)

---

## Installation

### Option A — Local pip

```bash
pip install tgops

# Verify
tgops --help
```

### Option B — Docker

```bash
# Pull or build
git clone https://github.com/[org]/tgops
cd tgops
docker build -t tgops .

# Run with an env file
docker run --rm -it \
  --env-file .env \
  -v tgops_data:/root/.tgops \
  tgops account setup
```

### Option C — Docker Compose

```bash
cp .env.example .env
# Edit .env with your credentials

# CLI only
docker compose up -d tgops

# CLI + REST API
docker compose --profile api up -d
```

---

## First-time Authentication

TGOps uses an interactive OTP wizard to authenticate your Telegram account session.

```bash
tgops account setup
```

You will be prompted for your phone number and the OTP sent by Telegram. The session file is saved to `~/.tgops/sessions/org_account` (configurable via `TGOPS_SESSION_PATH`).

Verify the session at any time:

```bash
tgops account verify
tgops account status
```

---

## First Migration Walkthrough

### 1. Inspect the source group

```bash
tgops group list
tgops group inspect 1234567890
```

### 2. Dry-run the migration plan

```bash
tgops migrate plan 1234567890
```

This prints the 10 steps without making any API calls.

### 3. Run the migration

```bash
tgops migrate run 1234567890 --new-title "My Community v2"
```

TGOps will:

1. Snapshot the source group
2. Create a new supergroup
3. Copy title and description
4. Generate an invite link for the new group
5. Verify 24h membership requirement for ownership transfer
6. Rename source group to `[ARCHIVED] <title>`
7. Pin a redirect message in the source group
8. Blast the invite link to all members (batched, rate-limited)
9. Register an auto-reply redirect handler
10. Mark the job complete and write the audit log

### 4. Monitor progress

```bash
tgops migrate status <job-id>
```

### 5. Resume a failed job

```bash
tgops migrate resume <job-id>
```

---

## REST API Quick Start (Phase 5)

```bash
# Set an API key (optional — leave empty for local-only use)
export TGOPS_API_KEY=mysecretkey

# Start the server
tgops serve --host 127.0.0.1 --port 8080

# Check health
curl http://localhost:8080/health

# Browse interactive docs
open http://localhost:8080/docs
```
