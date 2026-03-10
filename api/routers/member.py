"""Member offboarding endpoints."""
from __future__ import annotations

import glob
import json
import os

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_settings, verify_api_key
from api.schemas import (
    MemberFindResponse,
    OffboardingJobResponse,
    StartEmergencyRequest,
    StartOffboardingRequest,
)
from tgops.core.audit import AuditLogger
from tgops.core.client import TGOpsClient
from tgops.core.config import Settings
from tgops.models.member import OffboardingMode
from tgops.services.invite import InviteService
from tgops.services.member import MemberService

router = APIRouter(prefix="/member", tags=["member"])


def _job_to_response(job) -> dict:
    return {
        "job_id": job.job_id,
        "user_id": job.user_id,
        "username": job.username,
        "mode": job.mode.value if hasattr(job.mode, "value") else job.mode,
        "groups_found": job.groups_found,
        "groups_removed": job.groups_removed,
        "groups_skipped": job.groups_skipped,
        "groups_failed": job.groups_failed,
        "notify_message": job.notify_message,
        "status": job.status,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }


def _load_offboarding_job(job_id: str, settings: Settings) -> dict:
    path = os.path.join(settings.offboarding_dir, f"{job_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")
    with open(path) as f:
        return json.load(f)


@router.get("/find", response_model=MemberFindResponse, dependencies=[Depends(verify_api_key)])
async def find_member(user_id: int, settings: Settings = Depends(get_settings)):
    """Scan all managed groups for a user."""
    client = TGOpsClient(settings)
    audit = AuditLogger(settings.audit_log_path)
    invite_svc = InviteService(client, settings)
    svc = MemberService(client, audit, settings, invite_svc)
    async with client:
        record = await svc.find(user_id)
    return {
        "user_id": record.user_id,
        "username": record.username,
        "first_name": record.first_name,
        "last_name": record.last_name,
        "groups": record.groups,
        "is_active": {str(k): v for k, v in record.is_active.items()},
        "is_admin": {str(k): v for k, v in record.is_admin.items()},
        "found_at": record.found_at,
    }


@router.post("/offboard", response_model=OffboardingJobResponse, dependencies=[Depends(verify_api_key)])
async def offboard_member(body: StartOffboardingRequest, settings: Settings = Depends(get_settings)):
    """Start a planned offboarding job."""
    client = TGOpsClient(settings)
    audit = AuditLogger(settings.audit_log_path)
    invite_svc = InviteService(client, settings)
    svc = MemberService(client, audit, settings, invite_svc)
    async with client:
        job = await svc.offboard(body.user_id, body.message, OffboardingMode.PLANNED)
    return _job_to_response(job)


@router.post("/emergency", response_model=OffboardingJobResponse, dependencies=[Depends(verify_api_key)])
async def emergency_removal(body: StartEmergencyRequest, settings: Settings = Depends(get_settings)):
    """Start an emergency removal job. Minimal delays + invite rotation."""
    client = TGOpsClient(settings)
    audit = AuditLogger(settings.audit_log_path)
    invite_svc = InviteService(client, settings)
    svc = MemberService(client, audit, settings, invite_svc)
    async with client:
        job = await svc.offboard(body.user_id, body.message, OffboardingMode.EMERGENCY)
    return _job_to_response(job)


@router.get("/jobs", response_model=list[OffboardingJobResponse], dependencies=[Depends(verify_api_key)])
async def list_offboarding_jobs(settings: Settings = Depends(get_settings)):
    """List all offboarding jobs."""
    pattern = os.path.join(settings.offboarding_dir, "*.json")
    jobs = []
    for path in glob.glob(pattern):
        with open(path) as f:
            jobs.append(json.load(f))
    return sorted(jobs, key=lambda j: j.get("created_at", ""), reverse=True)


@router.get("/jobs/{job_id}", response_model=OffboardingJobResponse, dependencies=[Depends(verify_api_key)])
async def get_offboarding_job(job_id: str, settings: Settings = Depends(get_settings)):
    """Get an offboarding job by ID."""
    return _load_offboarding_job(job_id, settings)
