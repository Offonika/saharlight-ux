import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

ALLOWED_ROLES = {"patient", "clinician", "org_admin", "superadmin"}

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user_id = request.headers.get("X-User-Id")
        role = request.headers.get("X-Role", "patient")
        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=401, detail="invalid role")
        request.state.user_id = user_id
        request.state.role = role
        response = await call_next(request)
        return response


def require_role(*roles: str):
    async def dependency(request: Request) -> None:
        if getattr(request.state, "role", None) not in roles:
            raise HTTPException(status_code=403, detail="forbidden")
    return dependency
