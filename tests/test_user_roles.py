import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import services.api.app.main as server
from services.api.app.diabetes.services import db
from services.api.app.middleware.auth import AuthMiddleware
from services.api.app.services import user_roles


def setup_db(monkeypatch: pytest.MonkeyPatch) -> sessionmaker:
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
    with TestClient(server.app) as client:
        resp = client.get("/user/1/role")
        assert resp.status_code == 200
        assert resp.json() == {"role": "patient"}
        resp = client.put("/user/1/role", json={"role": "clinician"})
        assert resp.status_code == 200
        assert resp.json() == {"role": "clinician"}
        resp = client.get("/user/1/role")
        assert resp.status_code == 200
        assert resp.json() == {"role": "clinician"}

    with SessionLocal() as session:
        obj = session.get(db.UserRole, 1)
        assert obj is not None
        assert obj.role == "clinician"


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
