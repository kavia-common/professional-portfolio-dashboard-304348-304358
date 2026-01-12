from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, login_user, register_user


def test_contact_submit_public_success(client: TestClient):
    resp = client.post(
        "/contact/messages",
        json={
            "sender_name": "Alice",
            "sender_email": "alice@example.com",
            "subject": "Hello",
            "message": "This is a longer message body.",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["sender_email"] == "alice@example.com"
    assert body["status"] == "new"


def test_contact_list_messages_requires_admin(client: TestClient, user_credentials):
    # Normal user should be forbidden (403) because require_admin depends on get_current_user
    register_user(client, **user_credentials)
    _, p = login_user(client, username=user_credentials["username"], password=user_credentials["password"])
    token = p["access_token"]

    resp = client.get("/contact/messages", headers=auth_headers(token))
    assert resp.status_code == 403


def test_contact_list_messages_unauthenticated_401(client: TestClient):
    resp = client.get("/contact/messages")
    assert resp.status_code == 401


def test_contact_admin_can_list_and_update_status(client: TestClient, admin_user):
    # Create message
    create = client.post(
        "/contact/messages",
        json={
            "sender_name": "Bob",
            "sender_email": "bob@example.com",
            "subject": None,
            "message": "Please contact me back soon.",
        },
    )
    assert create.status_code == 201
    message_id = create.json()["id"]

    # Login admin
    status, payload = login_user(client, username=admin_user.username, password="adminpass123")
    token = payload["access_token"]

    inbox = client.get("/contact/messages", headers=auth_headers(token))
    assert inbox.status_code == 200
    ids = [m["id"] for m in inbox.json()]
    assert message_id in ids

    update = client.put(f"/contact/messages/{message_id}", headers=auth_headers(token), json={"status": "read"})
    assert update.status_code == 200
    assert update.json()["status"] == "read"


def test_contact_update_nonexistent_404(client: TestClient, admin_user):
    status, payload = login_user(client, username=admin_user.username, password="adminpass123")
    token = payload["access_token"]

    resp = client.put("/contact/messages/999999", headers=auth_headers(token), json={"status": "read"})
    assert resp.status_code == 404
