import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db
from services.api.app.middleware.auth import AuthMiddleware
from services.api.app.routers import users
from services.api.app.services import user_roles
from services.api.app.telegram_auth import require_tg_user


def setup_db(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(user_roles, "SessionLocal", SessionLocal)
    return SessionLocal


def test_role_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    SessionLocal = setup_db(monkeypatch)
    with SessionLocal() as session:
        session.add(db.UserRole(user_id=1, role="superadmin"))
        session.commit()

    app = FastAPI()
    app.include_router(users.router, prefix="/api")
    app.dependency_overrides[require_tg_user] = lambda: {"id": 1}

    with TestClient(app) as client:
        resp = client.get("/api/user/1/role")
        assert resp.status_code == 200
        assert resp.json() == {"role": "superadmin"}

        resp = client.put("/api/user/2/role", json={"role": "clinician"})
        assert resp.status_code == 200
        assert resp.json() == {"role": "clinician"}

        resp = client.get("/api/user/2/role")
        assert resp.status_code == 200
        assert resp.json() == {"role": "clinician"}

    with SessionLocal() as session:
        obj = session.get(db.UserRole, 2)
        assert obj is not None
        assert obj.role == "clinician"


def test_get_role_requires_token() -> None:
    app = FastAPI()
    app.include_router(users.router, prefix="/api")
    with TestClient(app) as client:
        resp = client.get("/api/user/1/role")
    assert resp.status_code == 401


def test_put_role_requires_token() -> None:
    app = FastAPI()
    app.include_router(users.router, prefix="/api")
    with TestClient(app) as client:
        resp = client.put("/api/user/1/role", json={"role": "clinician"})
    assert resp.status_code == 401


def test_put_role_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    setup_db(monkeypatch)
    app = FastAPI()
    app.include_router(users.router, prefix="/api")
    app.dependency_overrides[require_tg_user] = lambda: {"id": 1}
    with TestClient(app) as client:
        resp = client.put("/api/user/2/role", json={"role": "clinician"})
    assert resp.status_code == 403


def test_middleware_reads_role(monkeypatch: pytest.MonkeyPatch) -> None:
    SessionLocal = setup_db(monkeypatch)
    with SessionLocal() as session:
        session.add(db.UserRole(user_id=5, role="org_admin"))
        session.commit()

    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/whoami")
    async def whoami(req: Request) -> dict[str, int | str]:
        return {"user_id": req.state.user_id, "role": req.state.role}

    with TestClient(app) as client:
        resp = client.get("/whoami", headers={"X-User-Id": "5"})
        assert resp.status_code == 200
        assert resp.json() == {"user_id": 5, "role": "org_admin"}
