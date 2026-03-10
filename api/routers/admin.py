"""Admin management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_settings, verify_api_key
from api.schemas import AddAdminRequest, AdminResponse, RemoveAdminRequest
from tgops.core.audit import AuditLogger
from tgops.core.client import TGOpsClient
from tgops.core.config import Settings
from tgops.models.admin import AdminPrivileges
from tgops.services.admin import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_response(record) -> dict:
    return {
        "user_id": record.user_id,
        "username": record.username,
        "group_id": record.group_id,
        "added_by": record.added_by,
        "added_at": record.added_at,
        "removed_at": record.removed_at,
    }


@router.get("/{group_id}", response_model=list[AdminResponse], dependencies=[Depends(verify_api_key)])
async def list_admins(group_id: int, settings: Settings = Depends(get_settings)):
    """List admins for a group."""
    client = TGOpsClient(settings)
    audit = AuditLogger(settings.audit_log_path)
    svc = AdminService(client, audit, settings)
    async with client:
        admins = await svc.list(group_id)
    return [_to_response(a) for a in admins]


@router.post("/{group_id}", response_model=AdminResponse, dependencies=[Depends(verify_api_key)])
async def add_admin(group_id: int, body: AddAdminRequest, settings: Settings = Depends(get_settings)):
    """Promote a user to admin in a group."""
    client = TGOpsClient(settings)
    audit = AuditLogger(settings.audit_log_path)
    svc = AdminService(client, audit, settings)
    privileges = AdminPrivileges()
    async with client:
        record = await svc.add(group_id, body.user_id, body.title, privileges)
    return _to_response(record)


@router.delete("/{group_id}/{user_id}", dependencies=[Depends(verify_api_key)])
async def remove_admin(group_id: int, user_id: int, settings: Settings = Depends(get_settings)):
    """Demote an admin to member."""
    client = TGOpsClient(settings)
    audit = AuditLogger(settings.audit_log_path)
    svc = AdminService(client, audit, settings)
    async with client:
        await svc.remove(group_id, user_id)
    return {"ok": True}
