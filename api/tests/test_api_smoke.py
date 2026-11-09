from __future__ import annotations


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "sqlite"
    assert body["provider"] == "mock"
    assert isinstance(body["runs"], int)


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "FairScreen API"
