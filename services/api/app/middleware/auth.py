import logging
from typing import Awaitable, Callable

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

ALLOWED_ROLES = {"patient", "clinician", "org_admin", "superadmin"}

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        user_id_header = request.headers.get("X-User-Id")
        if user_id_header is None:
            raise HTTPException(status_code=401, detail="invalid user id")
        try:
            user_id = int(user_id_header)
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="invalid user id")

        role = request.headers.get("X-Role", "patient")
        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=401, detail="invalid role")
        request.state.user_id = user_id
        request.state.role = role
        response = await call_next(request)
        return response


def require_role(*roles: str) -> Callable[[Request], Awaitable[None]]:
    async def dependency(request: Request) -> None:
        if getattr(request.state, "role", None) not in roles:
            raise HTTPException(status_code=403, detail="forbidden")
    return dependency
