# FAQ

## Virtual Number Recommendations

You need a real or virtual phone number to create a Telegram account for your org account. Do **not** use your personal number.

### Recommended Providers

| Provider | Type | Notes |
|---|---|---|
| **Fragment** | Telegram-native anonymous numbers | Best option — numbers issued on TON blockchain, native Telegram integration. [fragment.com](https://fragment.com) |
| **HeroSMS** | Virtual SIM (online) | Reliable, supports Telegram OTP, pay per use. [herosms.com](https://herosms.com) |
| **5SIM** | Virtual SIM (online) | Large number inventory, competitive pricing. Good for testing. [5sim.net](https://5sim.net) |
| **Real SIM (physical)** | Physical SIM | Most reliable long-term; dedicated SIM in a spare phone or SIM modem. No dependency on third-party service. |

### Tips

- Fragment numbers are the most Telegram-native and least likely to be flagged.
- Avoid using free SMS services (e.g. receive-smss.com) — these numbers are shared and your session may be hijacked.
- For production use, a dedicated physical SIM is recommended for maximum reliability.
- Keep the number active — Telegram may require periodic re-verification.

---

## Telegram Terms of Service FAQ

### Is automating a Telegram account against the ToS?

Telegram's Terms of Service prohibit spam and mass unsolicited messaging. TGOps is designed for **legitimate community management** — migrating your own groups, offboarding members from groups you administer, and managing invite links. Used responsibly, this does not violate Telegram's ToS.

**Do not use TGOps to:**
- Send unsolicited messages to users who haven't opted in
- Scrape public groups at scale
- Bypass Telegram's anti-spam systems

### Will my account get banned?

TGOps includes built-in rate limiting (configurable via `TGOPS_BASE_DELAY_SECONDS`) and FloodWait handling to stay within Telegram's documented safe thresholds. Emergency mode uses a 1.0s floor (~30 ban-type actions/minute), which is the community-documented safe limit for bulk operations.

That said, no automation tool can guarantee zero risk. Always test with `--dry-run` first and start with small groups.

### Can I use a bot account instead?

No. Most management operations (transfer ownership, demote admins, kick members) require a real user account with admin privileges. Bot accounts have significantly restricted API access for these operations.

---

## Common Errors

### `FloodWait` errors

Telegram is rate-limiting your account. TGOps will automatically wait and retry (up to `TGOPS_MAX_FLOOD_RETRIES` times). If it persists, increase `TGOPS_BASE_DELAY_SECONDS`.

### `24h membership requirement not met`

The `transfer_ownership` step requires the org account to have been a member of the source group for at least 24 hours. Wait and then run `tgops migrate resume <job-id>`.

### `Session is NOT valid`

Your session file has expired or been invalidated. Run `tgops account setup` to re-authenticate.

### `Job file not found`

The job ID doesn't exist in `TGOPS_JOBS_DIR` / `TGOPS_OFFBOARDING_DIR`. Check the directory or use `tgops migrate status` / `tgops member status` to list available jobs.

### `Invalid or missing API key` (REST API)

You have set `TGOPS_API_KEY` but are not passing it as a Bearer token. Add `-H "Authorization: Bearer <your-key>"` to your curl commands, or leave `TGOPS_API_KEY` empty for local-only use.

### Docker: `Permission denied` on session file

The session file is written to `/root/.tgops/` inside the container, mounted as a named volume. If you're seeing permission errors, ensure the volume mount is correct and the container is running as root (the default Dockerfile uses root).

### `Cannot import hydrogram`

Install the required dependency: `pip install hydrogram`. If using Docker, rebuild the image.
