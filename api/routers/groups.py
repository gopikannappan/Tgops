"""Group endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_settings, verify_api_key
from api.schemas import GroupResponse
from tgops.core.audit import AuditLogger
from tgops.core.client import TGOpsClient
from tgops.core.config import Settings
from tgops.services.account import AccountService

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[GroupResponse], dependencies=[Depends(verify_api_key)])
async def list_groups(settings: Settings = Depends(get_settings)):
    """List all groups managed by the org account."""
    client = TGOpsClient(settings)
    audit = AuditLogger(settings.audit_log_path)
    svc = AccountService(client, settings)

    async with client:
        raw = await svc.status()

    # Return placeholder — full group list requires get_dialogs scan
    return []


@router.get("/{group_id}", response_model=GroupResponse, dependencies=[Depends(verify_api_key)])
async def get_group(group_id: int, settings: Settings = Depends(get_settings)):
    """Get details for a specific group."""
    from datetime import datetime
    # Full implementation requires MigrationService.snapshot — returns stub
    return {
        "group_id": group_id,
        "title": "Unknown",
        "username": None,
        "owner_user_id": 0,
        "member_count": 0,
        "invite_link": None,
        "is_archived": False,
        "snapshot_at": datetime.utcnow(),
    }
