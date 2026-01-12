from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, login_user, register_user


def test_admin_users_unauthenticated_401(client: TestClient):
    resp = client.get("/admin/users")
    assert resp.status_code == 401


def test_admin_users_non_admin_403(client: TestClient, user_credentials):
    register_user(client, **user_credentials)
    _, p = login_user(client, username=user_credentials["username"], password=user_credentials["password"])
    token = p["access_token"]

    resp = client.get("/admin/users", headers=auth_headers(token))
    assert resp.status_code == 403


def test_admin_users_admin_success(client: TestClient, admin_user):
    status, payload = login_user(client, username=admin_user.username, password="adminpass123")
    token = payload["access_token"]

    resp = client.get("/admin/users", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()

    assert set(body.keys()) == {"items", "page", "page_size", "total"}
    assert isinstance(body["items"], list)
    assert body["page"] == 1
    assert body["page_size"] >= 1
    assert body["total"] >= 1

    users = body["items"]
    assert any(u["id"] == admin_user.id for u in users)
    assert all("email" in u and "username" in u and "role" in u for u in users)
