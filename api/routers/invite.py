"""Invite link endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_settings, verify_api_key
from api.schemas import InviteRotateRequest, InviteRotateResponse
from tgops.core.client import TGOpsClient
from tgops.core.config import Settings
from tgops.services.invite import InviteService

router = APIRouter(prefix="/invite", tags=["invite"])


@router.post("/rotate", response_model=InviteRotateResponse, dependencies=[Depends(verify_api_key)])
async def rotate_invite(body: InviteRotateRequest, settings: Settings = Depends(get_settings)):
    """Rotate the invite link for a group."""
    client = TGOpsClient(settings)
    svc = InviteService(client, settings)
    async with client:
        new_link = await svc.rotate(body.group_id)
    return {"group_id": body.group_id, "new_link": new_link}
