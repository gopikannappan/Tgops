"""FastAPI dependencies — auth, settings, and service factories."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from tgops.core.config import Settings, load_config

_settings: Settings | None = None
_bearer = HTTPBearer(auto_error=False)


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_config()
    return _settings


def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    settings: Settings = Depends(get_settings),
) -> None:
    """Require a valid API key via Bearer token, unless no key is configured."""
    if not settings.api_key:
        # No key configured — allow all requests (local use)
        return
    if credentials is None or credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
