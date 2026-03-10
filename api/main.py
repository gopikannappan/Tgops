"""TGOps REST API — Phase 5.

Start with: tgops serve  (or: uvicorn api.main:app --host 127.0.0.1 --port 8080)

Auth: Bearer token via TGOPS_API_KEY env var. If empty, all requests are allowed (local use).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import account, admin, groups, invite, jobs, member

app = FastAPI(
    title="TGOps API",
    description="REST API for TGOps — Telegram community ops toolkit.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Pro UI dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(groups.router)
app.include_router(account.router)
app.include_router(invite.router)
app.include_router(admin.router)
app.include_router(member.router)


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}
