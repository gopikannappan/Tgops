"""Migration job endpoints."""
from __future__ import annotations

import glob
import json
import os

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_settings, verify_api_key
from api.schemas import MigrationJobResponse, StartMigrationRequest
from tgops.core.config import Settings

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _load_job(job_id: str, settings: Settings) -> dict:
    path = os.path.join(settings.jobs_dir, f"{job_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")
    with open(path) as f:
        return json.load(f)


def _list_jobs(settings: Settings) -> list[dict]:
    pattern = os.path.join(settings.jobs_dir, "*.json")
    jobs = []
    for path in glob.glob(pattern):
        with open(path) as f:
            jobs.append(json.load(f))
    return sorted(jobs, key=lambda j: j.get("created_at", ""), reverse=True)


@router.get("", response_model=list[MigrationJobResponse], dependencies=[Depends(verify_api_key)])
async def list_jobs(settings: Settings = Depends(get_settings)):
    """List all migration jobs."""
    return _list_jobs(settings)


@router.get("/{job_id}", response_model=MigrationJobResponse, dependencies=[Depends(verify_api_key)])
async def get_job(job_id: str, settings: Settings = Depends(get_settings)):
    """Get a migration job by ID."""
    return _load_job(job_id, settings)


@router.post("", response_model=MigrationJobResponse, status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_api_key)])
async def start_migration(body: StartMigrationRequest, settings: Settings = Depends(get_settings)):
    """Start a new migration job. Returns immediately — job runs asynchronously."""
    import asyncio
    import uuid

    from tgops.core.audit import AuditLogger
    from tgops.core.client import TGOpsClient
    from tgops.services.migration import MigrationService

    job_id = str(uuid.uuid4())
    client = TGOpsClient(settings)
    audit = AuditLogger(settings.audit_log_path)
    svc = MigrationService(client, audit, settings)

    # Run migration in background task
    async def _run():
        async with client:
            await svc.run(body.source_group_id, new_title=body.new_title)

    asyncio.create_task(_run())

    # Return a pending job representation immediately
    from datetime import datetime
    return {
        "job_id": job_id,
        "source_group_id": body.source_group_id,
        "target_group_id": None,
        "status": "PENDING",
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "error": None,
        "steps_completed": [],
    }
