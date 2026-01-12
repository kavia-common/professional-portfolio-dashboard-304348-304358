from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_headers, login_user, register_user


def _create_project(client: TestClient, token: str, payload: dict):
    return client.post("/projects", headers=auth_headers(token), json=payload)


def test_projects_list_unauthenticated_only_published(client: TestClient, user_credentials):
    # Create user + token
    reg = register_user(client, **user_credentials)
    assert reg["status"] == 201
    _, login_payload = login_user(client, username=user_credentials["username"], password=user_credentials["password"])
    token = login_payload["access_token"]

    # Create a draft and a published project
    r1 = _create_project(
        client,
        token,
        {"title": "Draft project", "description": None, "repo_url": None, "live_url": None, "status": "draft", "skill_ids": []},
    )
    assert r1.status_code == 201

    r2 = _create_project(
        client,
        token,
        {"title": "Published project", "description": None, "repo_url": None, "live_url": None, "status": "published", "skill_ids": []},
    )
    assert r2.status_code == 201

    resp_public = client.get("/projects")
    assert resp_public.status_code == 200
    body = resp_public.json()
    assert set(body.keys()) == {"items", "page", "page_size", "total"}

    titles = [p["title"] for p in body["items"]]
    assert "Published project" in titles
    assert "Draft project" not in titles


def test_projects_create_requires_auth(client: TestClient):
    resp = client.post("/projects", json={"title": "X", "status": "draft"})
    assert resp.status_code == 401


def test_projects_get_nonexistent_404(client: TestClient):
    resp = client.get("/projects/999999")
    assert resp.status_code == 404


def test_projects_owner_can_update_and_delete(client: TestClient, user_credentials):
    register_user(client, **user_credentials)
    _, login_payload = login_user(client, username=user_credentials["username"], password=user_credentials["password"])
    token = login_payload["access_token"]

    created = _create_project(
        client,
        token,
        {"title": "My project", "description": "d", "repo_url": None, "live_url": None, "status": "draft", "skill_ids": []},
    )
    assert created.status_code == 201
    project_id = created.json()["id"]

    upd = client.put(f"/projects/{project_id}", headers=auth_headers(token), json={"title": "My project updated"})
    assert upd.status_code == 200
    assert upd.json()["title"] == "My project updated"

    delete = client.delete(f"/projects/{project_id}", headers=auth_headers(token))
    assert delete.status_code == 204

    # Now should be missing
    get_after = client.get(f"/projects/{project_id}", headers=auth_headers(token))
    assert get_after.status_code == 404


def test_projects_other_user_cannot_update_or_delete(client: TestClient):
    # user1 creates project
    c1 = {"email": "u1@example.com", "username": "user1x", "password": "password123"}
    c2 = {"email": "u2@example.com", "username": "user2x", "password": "password123"}

    assert register_user(client, **c1)["status"] == 201
    assert register_user(client, **c2)["status"] == 201

    _, p1 = login_user(client, username=c1["username"], password=c1["password"])
    _, p2 = login_user(client, username=c2["username"], password=c2["password"])
    t1, t2 = p1["access_token"], p2["access_token"]

    created = _create_project(
        client,
        t1,
        {"title": "User1 Draft", "description": None, "repo_url": None, "live_url": None, "status": "draft", "skill_ids": []},
    )
    project_id = created.json()["id"]

    upd = client.put(f"/projects/{project_id}", headers=auth_headers(t2), json={"title": "hacked"})
    assert upd.status_code == 403

    delete = client.delete(f"/projects/{project_id}", headers=auth_headers(t2))
    assert delete.status_code == 403


def test_projects_create_invalid_skill_ids_returns_400(client: TestClient, user_credentials):
    register_user(client, **user_credentials)
    _, p = login_user(client, username=user_credentials["username"], password=user_credentials["password"])
    token = p["access_token"]

    resp = _create_project(
        client,
        token,
        {"title": "With bad skills", "description": None, "repo_url": None, "live_url": None, "status": "draft", "skill_ids": [9999]},
    )
    assert resp.status_code == 400
    assert "skill_ids" in resp.json()["detail"]


def test_projects_list_pagination_params_work(client: TestClient, user_credentials):
    # Create user + token
    assert register_user(client, **user_credentials)["status"] == 201
    _, login_payload = login_user(client, username=user_credentials["username"], password=user_credentials["password"])
    token = login_payload["access_token"]

    # Create multiple published projects
    for i in range(1, 6):
        r = _create_project(
            client,
            token,
            {"title": f"P{i}", "description": None, "repo_url": None, "live_url": None, "status": "published", "skill_ids": []},
        )
        assert r.status_code == 201

    page1 = client.get("/projects?page=1&page_size=2")
    assert page1.status_code == 200
    body1 = page1.json()
    assert body1["page"] == 1
    assert body1["page_size"] == 2
    assert body1["total"] >= 5
    assert len(body1["items"]) == 2

    page2 = client.get("/projects?page=2&page_size=2")
    assert page2.status_code == 200
    body2 = page2.json()
    assert body2["page"] == 2
    assert len(body2["items"]) == 2
