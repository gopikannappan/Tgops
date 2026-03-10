# CLI Commands

```
tgops [OPTIONS] COMMAND [ARGS]...
```

**Global options:**

| Option | Description |
|---|---|
| `--config PATH` | Path to tgops.yaml config file |
| `--dry-run` | Skip all destructive API calls |
| `--verbose` / `-v` | Enable verbose (DEBUG) logging |
| `--help` | Show help and exit |

---

## account

Manage the Telegram org account session.

### `tgops account setup`

Interactive OTP wizard — authenticate the org account. Run this once before any other command.

```bash
tgops account setup
```

### `tgops account status`

Show current account status, session path, and group count.

```bash
tgops account status
```

### `tgops account verify`

Check that the saved session is valid and authorized.

```bash
tgops account verify
```

---

## group

Inspect and snapshot groups.

### `tgops group list`

List all groups the org account is a member of.

```bash
tgops group list
```

### `tgops group inspect GROUP_ID`

Show detailed info about a specific group.

```bash
tgops group inspect 1234567890
```

### `tgops group snapshot GROUP_ID`

Capture a GroupState snapshot to JSON and the audit log.

```bash
# Print to stdout
tgops group snapshot 1234567890

# Save to file
tgops group snapshot 1234567890 --output snapshot.json
```

---

## migrate

Run and manage group migrations.

### `tgops migrate plan GROUP_ID`

Show the 10-step migration plan without making any API calls.

```bash
tgops migrate plan 1234567890
```

### `tgops migrate run GROUP_ID`

Execute a full 10-step group migration.

```bash
tgops migrate run 1234567890
tgops migrate run 1234567890 --new-title "My Community v2"
tgops migrate run 1234567890 --no-confirm  # Skip confirmation prompt
```

### `tgops migrate status JOB_ID`

Show the current status of a migration job.

```bash
tgops migrate status a1b2c3d4-...
```

### `tgops migrate resume JOB_ID`

Resume a failed or interrupted migration from the last completed step.

```bash
tgops migrate resume a1b2c3d4-...
```

### `tgops migrate batch`

Run sequential migrations for multiple groups listed in a file.

```bash
# groups.txt — one group ID per line, # for comments
tgops migrate batch --file groups.txt
tgops migrate batch --file groups.txt --concurrency 1
```

---

## admin

Manage group admin rosters.

### `tgops admin list GROUP_ID`

List all admins in a group.

```bash
tgops admin list 1234567890
```

### `tgops admin add GROUP_ID USER_ID`

Promote a user to admin.

```bash
tgops admin add 1234567890 987654321
tgops admin add 1234567890 987654321 --title "Moderator"
tgops admin add 1234567890 987654321 --privileges "delete,ban,invite"
```

Available privileges: `change_info`, `post`, `edit`, `delete`, `ban`, `invite`, `pin`, `video`, `anon`

### `tgops admin remove GROUP_ID USER_ID`

Demote an admin back to regular member.

```bash
tgops admin remove 1234567890 987654321
```

### `tgops admin export GROUP_ID`

Export admin roster to CSV.

```bash
tgops admin export 1234567890
tgops admin export 1234567890 --output admins.csv
```

### `tgops admin sync GROUP_ID`

Sync admin roster from a CSV file.

```bash
tgops admin sync 1234567890 --roster admins.csv
tgops admin sync 1234567890 --roster admins.csv --remove  # Remove admins not in CSV
```

---

## invite

Manage group invite links.

### `tgops invite rotate GROUP_ID`

Revoke the current invite link and create a new one.

```bash
tgops invite rotate 1234567890
```

### `tgops invite status GROUP_ID`

Show current invite link info for a group.

```bash
tgops invite status 1234567890
```

---

## member

Member lookup and offboarding.

### `tgops member find USER_ID`

Scan all managed groups and show a user's membership status.

```bash
tgops member find 987654321
```

### `tgops member offboard USER_ID`

Remove a user from all managed groups (planned mode — human-like delays).

```bash
tgops member offboard 987654321
tgops member offboard 987654321 --message "Your access has been revoked."
tgops member offboard 987654321 --no-confirm
```

### `tgops member emergency USER_ID`

Emergency removal — minimal delays + rotate all invite links.

```bash
tgops member emergency 987654321
tgops member emergency 987654321 --message "Security policy violation."
```

### `tgops member ban USER_ID`

Ban a user from specified groups (or all managed groups).

```bash
tgops member ban 987654321
tgops member ban 987654321 --groups "1234567890,9876543210"
```

### `tgops member status JOB_ID`

Show the status of an offboarding job.

```bash
tgops member status a1b2c3d4-...
```

---

## serve

Start the Phase 5 REST API server.

```bash
tgops serve
tgops serve --host 0.0.0.0 --port 9090
```

See [REST API](api.md) for full endpoint documentation.
