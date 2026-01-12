from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, login_user, register_user


def test_skills_list_public(client: TestClient):
    resp = client.get("/skills")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"items", "page", "page_size", "total"}
    assert isinstance(body["items"], list)


def test_skills_create_requires_admin_403_for_normal_user(client: TestClient, user_credentials):
    register_user(client, **user_credentials)
    _, p = login_user(client, username=user_credentials["username"], password=user_credentials["password"])
    token = p["access_token"]

    resp = client.post("/skills", headers=auth_headers(token), json={"name": "Python", "category": "Backend", "level": 4})
    assert resp.status_code == 403


def test_skills_create_update_delete_admin_success(client: TestClient, admin_user):
    # Login admin to obtain token
    status, payload = login_user(client, username=admin_user.username, password="adminpass123")
    assert status == 200
    token = payload["access_token"]

    created = client.post("/skills", headers=auth_headers(token), json={"name": "GoLang", "category": "Backend", "level": 3})
    assert created.status_code == 201
    skill_id = created.json()["id"]

    updated = client.put(f"/skills/{skill_id}", headers=auth_headers(token), json={"category": "Systems", "level": 5})
    assert updated.status_code == 200
    assert updated.json()["level"] == 5

    deleted = client.delete(f"/skills/{skill_id}", headers=auth_headers(token))
    assert deleted.status_code == 204

    # Now deleting again should 404
    deleted_again = client.delete(f"/skills/{skill_id}", headers=auth_headers(token))
    assert deleted_again.status_code == 404


def test_skills_create_duplicate_name_409(client: TestClient, admin_user):
    status, payload = login_user(client, username=admin_user.username, password="adminpass123")
    token = payload["access_token"]

    r1 = client.post("/skills", headers=auth_headers(token), json={"name": "React", "category": "Frontend", "level": 4})
    assert r1.status_code == 201

    r2 = client.post("/skills", headers=auth_headers(token), json={"name": "React", "category": "Frontend", "level": 4})
    assert r2.status_code == 409
