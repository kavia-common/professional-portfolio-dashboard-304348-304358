from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, login_user, register_user


def test_profile_requires_auth(client: TestClient):
    resp = client.get("/profile/me")
    assert resp.status_code == 401


def test_profile_get_me_creates_profile_if_missing(client: TestClient, user_credentials):
    reg = register_user(client, **user_credentials)
    assert reg["status"] == 201

    status, payload = login_user(client, username=user_credentials["username"], password=user_credentials["password"])
    assert status == 200
    token = payload["access_token"]

    resp = client.get("/profile/me", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == reg["json"]["id"]
    assert "id" in body
    assert "updated_at" in body
    assert isinstance(body.get("socials"), dict)


def test_profile_update_me_persists_fields(client: TestClient, user_credentials):
    reg = register_user(client, **user_credentials)
    assert reg["status"] == 201
    status, payload = login_user(client, username=user_credentials["username"], password=user_credentials["password"])
    token = payload["access_token"]

    update = {
        "full_name": "Test User",
        "bio": "Hello world",
        "location": "Earth",
        "website": "https://example.com",
        "socials": {"github": "https://github.com/test"},
    }
    resp = client.put("/profile/me", headers=auth_headers(token), json=update)
    assert resp.status_code == 200
    body = resp.json()
    assert body["full_name"] == "Test User"
    assert body["bio"] == "Hello world"
    assert body["socials"]["github"].endswith("/test")
