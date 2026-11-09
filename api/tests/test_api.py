from __future__ import annotations


def _create_run(client, **overrides):
    payload = {
        "name": "API test run",
        "provider": "mock",
        "models": ["Mock-Screen-A"],
        "mitigations": ["none", "combined"],
        "seed": 5,
        "repeats": 1,
        "budget_cap_usd": 5.0,
        "shortlist_cutoff": 7.0,
        "temperature": 0.2,
        "bases_per_role": 1,
        "execute": True,
    }
    payload.update(overrides)
    response = client.post("/runs", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_run_executes_scores_and_audits(client):
    data = _create_run(client)
    assert data["status"] == "completed"
    assert data["is_simulated"] is True
    assert data["variants"] == 60
    assert data["scores"] == 120
    assert data["total_scores"] == 120
    assert data["percent"] == 100.0
    assert data["audit_count"] > 0
    assert data["accuracy_count"] == 2


def test_dashboard_and_related_endpoints(client):
    data = _create_run(client)
    run_id = data["id"]
    dashboard = client.get(f"/runs/{run_id}/dashboard").json()
    assert dashboard["run"]["id"] == run_id
    assert dashboard["run"]["is_simulated"] is True
    assert dashboard["verdict"]["models"]
    assert dashboard["audits"]
    assert len(dashboard["accuracy"]) == 2
    assert dashboard["shortlist"]
    assert dashboard["progress"]["percent"] == 100.0

    verdict = client.get(f"/runs/{run_id}/verdict").json()
    assert verdict["run_id"] == run_id
    assert verdict["models"][0]["model"] == "Mock-Screen-A"
    assert "summary" in verdict["models"][0]

    audits = client.get(f"/runs/{run_id}/audits?mitigation=none").json()
    assert audits["total"] == 8
    assert all(item["mitigation"] == "none" for item in audits["items"])

    accuracy = client.get(f"/runs/{run_id}/accuracy?mitigation=none").json()
    assert accuracy["total"] == 1
    assert 0.0 <= accuracy["items"][0]["pairwise_accuracy"] <= 1.0

    shortlist = client.get(f"/runs/{run_id}/shortlist?mitigation=none").json()
    assert shortlist["total"] == 8
    assert "shortlist_ratio" in shortlist["items"][0]

    progress = client.get(f"/runs/{run_id}/progress").json()
    assert progress["status"] == "completed"
    assert progress["completed"] == progress["total"]


def test_runs_list_and_detail(client):
    data = _create_run(client)
    listing = client.get("/runs").json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == data["id"]
    assert listing["items"][0]["models"][0]["mitigation"] == "none"

    detail = client.get(f"/runs/{data['id']}").json()
    assert detail["id"] == data["id"]
    assert detail["audit_count"] > 0


def test_scores_and_pairs_endpoints(client):
    data = _create_run(client)
    run_id = data["id"]
    scores = client.get(
        f"/runs/{run_id}/scores?mitigation=none&attribute=gender&limit=5"
    ).json()
    assert scores["total"] == 12
    assert len(scores["items"]) == 5
    assert scores["items"][0]["attribute"] == "gender"
    assert scores["items"][0]["label"]
    assert "prompt_text" not in scores["items"][0]

    with_prompt = client.get(
        f"/runs/{run_id}/scores?mitigation=none&attribute=gender&include_prompt=true&limit=1"
    ).json()
    assert "prompt_text" in with_prompt["items"][0]

    pairs = client.get(
        f"/runs/{run_id}/pairs?model=Mock-Screen-A&mitigation=none&attribute=gender&limit=3"
    ).json()
    assert pairs["total"] == 6
    assert len(pairs["items"]) == 3
    first = pairs["items"][0]
    assert first["group_a"] == "woman"
    assert first["group_b"] == "man"
    assert first["text_a"] != first["text_b"]
    assert first["gap"] == first["score_a"] - first["score_b"]


def test_csv_export(client):
    data = _create_run(client)
    response = client.get(f"/runs/{data['id']}/export/csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.headers["x-fairscreen-simulated"] == "true"
    assert "attachment" in response.headers["content-disposition"]
    body = response.text
    assert body.startswith("table,simulated,run_id,run_name")
    assert "audit" in body
    assert "accuracy" in body
    assert data["id"] in body


def test_markdown_export(client):
    data = _create_run(client)
    response = client.get(f"/runs/{data['id']}/export/markdown")
    assert response.status_code == 200
    assert "text/markdown" in response.headers["content-type"]
    body = response.text
    assert "# FairScreen report: API test run" in body
    assert "**Simulated data.**" in body
    assert "## Verdict" in body
    assert "## Audit table" in body
    assert "## Accuracy" in body
    assert "## Method and limits" in body


def test_create_without_execute_then_execute(client):
    data = _create_run(client, execute=False)
    assert data["status"] == "pending"
    assert data["scores"] == 0
    response = client.post(f"/runs/{data['id']}/execute")
    assert response.status_code == 200
    executed = response.json()
    assert executed["status"] == "completed"
    assert executed["scores"] == 120
    assert executed["audit_count"] > 0


def test_unknown_run_returns_404(client):
    for path in [
        "/runs/missing",
        "/runs/missing/progress",
        "/runs/missing/audits",
        "/runs/missing/accuracy",
        "/runs/missing/shortlist",
        "/runs/missing/verdict",
        "/runs/missing/dashboard",
        "/runs/missing/scores",
        "/runs/missing/pairs",
        "/runs/missing/export/csv",
        "/runs/missing/export/markdown",
    ]:
        assert client.get(path).status_code == 404


def test_invalid_mitigation_returns_400(client):
    response = client.post(
        "/runs",
        json={
            "name": "bad",
            "provider": "mock",
            "models": ["Mock-Screen-A"],
            "mitigations": ["magic"],
            "execute": False,
            "bases_per_role": 1,
        },
    )
    assert response.status_code == 400
    assert "Unknown mitigations" in response.text
