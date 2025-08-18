import logging
from typing import Awaitable, Callable

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger(__name__)

ALLOWED_ROLES = {"patient", "clinician", "org_admin", "superadmin"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        user_id_header = request.headers.get("X-User-Id")
        if user_id_header is None:
            logger.warning(
                "Missing X-User-Id for request %s %s",
                request.method,
                request.url.path,
            )
            raise HTTPException(status_code=401, detail="invalid user id")
        try:
            user_id = int(user_id_header)
        except (TypeError, ValueError):
            logger.warning(
                "Invalid X-User-Id %r for request %s %s",
                user_id_header,
                request.method,
                request.url.path,
            )
            raise HTTPException(status_code=401, detail="invalid user id")

        role = request.headers.get("X-Role", "patient")
        if role not in ALLOWED_ROLES:
            logger.warning(
                "Invalid X-Role %r for request %s %s",
                role,
                request.method,
                request.url.path,
            )
            raise HTTPException(status_code=401, detail="invalid role")
        request.state.user_id = user_id
        request.state.role = role
        response = await call_next(request)
        return response


def require_role(*roles: str) -> Callable[[Request], Awaitable[None]]:
    async def dependency(request: Request) -> None:
        if getattr(request.state, "role", None) not in roles:
            logger.warning(
                "Forbidden access for role %r to %s %s",
                getattr(request.state, "role", None),
                request.method,
                request.url.path,
            )
            raise HTTPException(status_code=403, detail="forbidden")
    return dependency
