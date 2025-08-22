import logging
import os
from typing import Awaitable, Callable

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from ..config import settings
from ..telegram_auth import TG_INIT_DATA_HEADER, parse_and_verify_init_data

logger = logging.getLogger(__name__)

ALLOWED_ROLES = {"patient", "clinician", "org_admin", "superadmin"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        tg_init_data = request.headers.get(TG_INIT_DATA_HEADER)
        if tg_init_data is not None:
            token: str | None = os.getenv("TELEGRAM_TOKEN") or settings.telegram_token
            if not token:
                logger.error("telegram token not configured")
                raise HTTPException(status_code=500, detail="server misconfigured")
            data = parse_and_verify_init_data(tg_init_data, token)
            user = data.get("user")
            if not isinstance(user, dict) or "id" not in user:
                raise HTTPException(status_code=401, detail="invalid user")
            try:
                user_id = int(user["id"])
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=401, detail="invalid user id") from exc
            role = "patient"
        else:
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
