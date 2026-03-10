# REST API (Phase 5)

TGOps ships a FastAPI-based REST API for integration with CI/CD pipelines, dashboards, and external tools.

## Starting the Server

```bash
# Via CLI
tgops serve

# Via uvicorn directly
uvicorn api.main:app --host 127.0.0.1 --port 8080

# Via Docker Compose (profile)
docker compose --profile api up -d
```

Interactive docs are available at:

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

---

## Authentication

Set `TGOPS_API_KEY` to a secret string to require a Bearer token on all requests.

```bash
export TGOPS_API_KEY=mysecretkey
```

Then pass it as a Bearer token:

```bash
curl -H "Authorization: Bearer mysecretkey" http://localhost:8080/jobs
```

If `TGOPS_API_KEY` is empty (the default), all requests are allowed — suitable for local/private use only.

---

## Endpoints

### Health

#### `GET /health`

```bash
curl http://localhost:8080/health
# {"status":"ok"}
```

---

### Jobs (Migration)

#### `GET /jobs`

List all migration jobs, sorted newest first.

```bash
curl -H "Authorization: Bearer $KEY" http://localhost:8080/jobs
```

#### `GET /jobs/{job_id}`

Get a migration job by ID.

```bash
curl -H "Authorization: Bearer $KEY" http://localhost:8080/jobs/a1b2c3d4-...
```

#### `POST /jobs`

Start a new migration job. Returns `202 Accepted` immediately; the job runs asynchronously.

```bash
curl -X POST http://localhost:8080/jobs \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"source_group_id": 1234567890, "new_title": "My Community v2"}'
```

Response:

```json
{
  "job_id": "a1b2c3d4-...",
  "source_group_id": 1234567890,
  "target_group_id": null,
  "status": "PENDING",
  "created_at": "2026-03-10T12:00:00",
  "completed_at": null,
  "error": null,
  "steps_completed": []
}
```

---

### Groups

#### `GET /groups`

List all managed groups (returns current placeholder; full scan requires dialog iteration).

```bash
curl -H "Authorization: Bearer $KEY" http://localhost:8080/groups
```

#### `GET /groups/{group_id}`

Get details for a specific group.

```bash
curl -H "Authorization: Bearer $KEY" http://localhost:8080/groups/1234567890
```

---

### Account

#### `GET /account/status`

Get org account health — auth status, session, group count.

```bash
curl -H "Authorization: Bearer $KEY" http://localhost:8080/account/status
```

Response:

```json
{
  "is_authorized": true,
  "phone": "+15551234567",
  "session_path": "/root/.tgops/sessions/org_account",
  "me": {"id": 123456, "first_name": "Org", "username": "orgbot"},
  "group_count": 12
}
```

---

### Invite

#### `POST /invite/rotate`

Rotate the invite link for a group.

```bash
curl -X POST http://localhost:8080/invite/rotate \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"group_id": 1234567890}'
```

Response:

```json
{
  "group_id": 1234567890,
  "new_link": "https://t.me/joinchat/XXXXXXXXXX"
}
```

---

### Admin

#### `GET /admin/{group_id}`

List admins for a group.

```bash
curl -H "Authorization: Bearer $KEY" http://localhost:8080/admin/1234567890
```

#### `POST /admin/{group_id}`

Promote a user to admin.

```bash
curl -X POST http://localhost:8080/admin/1234567890 \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 987654321, "title": "Moderator", "privileges": ["delete", "ban"]}'
```

#### `DELETE /admin/{group_id}/{user_id}`

Demote an admin to member.

```bash
curl -X DELETE http://localhost:8080/admin/1234567890/987654321 \
  -H "Authorization: Bearer $KEY"
```

---

### Member

#### `GET /member/find?user_id={user_id}`

Scan all managed groups for a user.

```bash
curl -H "Authorization: Bearer $KEY" "http://localhost:8080/member/find?user_id=987654321"
```

Response:

```json
{
  "user_id": 987654321,
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "groups": [1234567890, 9876543210],
  "is_active": {"1234567890": true, "9876543210": false},
  "is_admin": {"1234567890": false, "9876543210": false},
  "found_at": "2026-03-10T12:00:00"
}
```

#### `POST /member/offboard`

Start a planned offboarding job.

```bash
curl -X POST http://localhost:8080/member/offboard \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 987654321, "message": "Your access has been revoked."}'
```

#### `POST /member/emergency`

Start an emergency removal job (minimal delays + invite rotation).

```bash
curl -X POST http://localhost:8080/member/emergency \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 987654321, "message": "Security violation."}'
```

#### `GET /member/jobs`

List all offboarding jobs.

```bash
curl -H "Authorization: Bearer $KEY" http://localhost:8080/member/jobs
```

#### `GET /member/jobs/{job_id}`

Get an offboarding job by ID.

```bash
curl -H "Authorization: Bearer $KEY" http://localhost:8080/member/jobs/a1b2c3d4-...
```
