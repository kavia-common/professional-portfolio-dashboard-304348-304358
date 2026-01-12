from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import login_user, register_user


def test_register_and_login_success(client: TestClient, user_credentials):
    reg = register_user(client, **user_credentials)
    assert reg["status"] == 201
    assert reg["json"]["email"] == user_credentials["email"]
    assert reg["json"]["username"] == user_credentials["username"]
    assert reg["json"]["role"] == "user"
    assert "id" in reg["json"]

    status, payload = login_user(client, username=user_credentials["username"], password=user_credentials["password"])
    assert status == 200
    assert "access_token" in payload
    assert payload.get("token_type") == "bearer"


def test_register_duplicate_username_or_email_returns_409(client: TestClient, user_credentials):
    reg1 = register_user(client, **user_credentials)
    assert reg1["status"] == 201

    # Duplicate username/email should hit the pre-check and return 409
    reg2 = register_user(client, **user_credentials)
    assert reg2["status"] == 409
    assert reg2["json"]["detail"].lower().find("exists") != -1


def test_register_validation_errors_return_422(client: TestClient):
    # Invalid email + too-short password
    resp = client.post("/auth/register", json={"email": "not-an-email", "username": "ab", "password": "short"})
    assert resp.status_code == 422


def test_login_bad_credentials_returns_401(client: TestClient, user_credentials):
    reg = register_user(client, **user_credentials)
    assert reg["status"] == 201

    status, payload = login_user(client, username=user_credentials["username"], password="wrong-password")
    assert status == 401
    assert "detail" in payload
