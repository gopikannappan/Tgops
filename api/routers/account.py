"""Account health endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_settings, verify_api_key
from api.schemas import AccountStatusResponse
from tgops.core.audit import AuditLogger
from tgops.core.client import TGOpsClient
from tgops.core.config import Settings
from tgops.services.account import AccountService

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/status", response_model=AccountStatusResponse, dependencies=[Depends(verify_api_key)])
async def account_status(settings: Settings = Depends(get_settings)):
    """Get org account health — auth status, session, group count."""
    client = TGOpsClient(settings)
    svc = AccountService(client, settings)
    async with client:
        info = await svc.status()
    return info
