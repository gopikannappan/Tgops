"""Pydantic schemas for the TGOps REST API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


# ── Migration ──────────────────────────────────────────────────────────────────

class MigrationJobResponse(BaseModel):
    job_id: str
    source_group_id: int
    target_group_id: int | None
    status: str
    created_at: datetime
    completed_at: datetime | None
    error: str | None
    steps_completed: list[str]


class StartMigrationRequest(BaseModel):
    source_group_id: int
    new_title: str | None = None


# ── Groups ─────────────────────────────────────────────────────────────────────

class GroupResponse(BaseModel):
    group_id: int
    title: str
    username: str | None
    owner_user_id: int
    member_count: int
    invite_link: str | None
    is_archived: bool
    snapshot_at: datetime


# ── Account ────────────────────────────────────────────────────────────────────

class AccountStatusResponse(BaseModel):
    is_authorized: bool
    phone: str
    session_path: str
    me: dict[str, Any] | None
    group_count: int


# ── Invite ─────────────────────────────────────────────────────────────────────

class InviteRotateRequest(BaseModel):
    group_id: int


class InviteRotateResponse(BaseModel):
    group_id: int
    new_link: str


# ── Admin ──────────────────────────────────────────────────────────────────────

class AdminResponse(BaseModel):
    user_id: int
    username: str | None
    group_id: int
    added_by: int
    added_at: datetime
    removed_at: datetime | None


class AddAdminRequest(BaseModel):
    user_id: int
    title: str | None = None
    privileges: list[str] = []


class RemoveAdminRequest(BaseModel):
    user_id: int


# ── Member ─────────────────────────────────────────────────────────────────────

class MemberFindResponse(BaseModel):
    user_id: int
    username: str | None
    first_name: str
    last_name: str | None
    groups: list[int]
    is_active: dict[str, bool]
    is_admin: dict[str, bool]
    found_at: datetime


class OffboardingJobResponse(BaseModel):
    job_id: str
    user_id: int
    username: str | None
    mode: str
    groups_found: list[int]
    groups_removed: list[int]
    groups_skipped: list[int]
    groups_failed: list[int]
    notify_message: str | None
    status: str
    created_at: datetime
    completed_at: datetime | None


class StartOffboardingRequest(BaseModel):
    user_id: int
    message: str | None = None


class StartEmergencyRequest(BaseModel):
    user_id: int
    message: str | None = None


# ── Common ─────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str
