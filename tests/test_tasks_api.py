from taskdeck import create_app
from taskdeck.config import Config


def _create(client, **fields):
    payload = {"title": "demo"}
    payload.update(fields)
    return client.post("/api/tasks", json=payload)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    assert body["runner"] == "none"


def test_create_and_list(client):
    r = _create(client, title="buy milk", project="home", tags=["errand"])
    assert r.status_code == 201
    task = r.get_json()["task"]
    assert task["title"] == "buy milk"
    assert task["status"] == "todo"
    assert task["run_status"] == "none"
    assert task["tags"] == ["errand"]

    listing = client.get("/api/tasks")
    assert listing.status_code == 200
    tasks = listing.get_json()["tasks"]
    assert len(tasks) == 1 and tasks[0]["id"] == task["id"]


def test_create_requires_title(client):
    assert client.post("/api/tasks", json={"title": "   "}).status_code == 400
    assert client.post("/api/tasks", json={}).status_code == 400


def test_create_rejects_bad_tags(client):
    r = client.post("/api/tasks", json={"title": "x", "tags": "nope"})
    assert r.status_code == 400


def test_filter_by_status_and_project(client):
    _create(client, title="a", project="p1")
    second = _create(client, title="b", project="p2").get_json()["task"]
    client.put("/api/tasks/%d" % second["id"], json={"status": "doing"})

    p1 = client.get("/api/tasks?project=p1").get_json()["tasks"]
    assert len(p1) == 1 and p1[0]["title"] == "a"

    doing = client.get("/api/tasks?status=doing").get_json()["tasks"]
    assert len(doing) == 1 and doing[0]["id"] == second["id"]


def test_update_status_move(client):
    tid = _create(client).get_json()["task"]["id"]
    r = client.put("/api/tasks/%d" % tid, json={"status": "review"})
    assert r.status_code == 200
    assert r.get_json()["task"]["status"] == "review"


def test_update_invalid_status(client):
    tid = _create(client).get_json()["task"]["id"]
    r = client.put("/api/tasks/%d" % tid, json={"status": "bogus"})
    assert r.status_code == 400


def test_update_not_found(client):
    assert client.put("/api/tasks/999", json={"status": "done"}).status_code == 404


def test_delete(client):
    tid = _create(client).get_json()["task"]["id"]
    assert client.delete("/api/tasks/%d" % tid).status_code == 204
    assert client.delete("/api/tasks/%d" % tid).status_code == 404


def test_runner_endpoint_absent_when_disabled(client):
    tid = _create(client).get_json()["task"]["id"]
    # runner disabled -> run blueprint not mounted -> 404
    assert client.post("/api/tasks/%d/run" % tid).status_code == 404


def test_create_rejects_non_string_fields(client):
    for bad in ({"title": "t", "body": [1, 2]},
                {"title": "t", "project": {"x": 1}},
                {"title": "t", "due_date": 5},
                {"title": 123}):
        assert client.post("/api/tasks", json=bad).status_code == 400


def test_update_rejects_non_string_fields(client):
    tid = _create(client).get_json()["task"]["id"]
    assert client.put("/api/tasks/%d" % tid, json={"body": [1]}).status_code == 400


def test_create_rejects_oversized_title(client):
    assert client.post("/api/tasks", json={"title": "x" * 2000}).status_code == 400


def test_timestamp_is_utc(client):
    task = _create(client).get_json()["task"]
    assert task["created_at"].endswith("Z")


def test_oversized_task_id_is_not_found(client):
    big = 2 ** 63 + 5  # outside SQLite's signed-64-bit range
    assert client.put("/api/tasks/%d" % big, json={"status": "done"}).status_code == 404
    assert client.delete("/api/tasks/%d" % big).status_code == 404


def test_filter_by_due_date(client):
    client.post("/api/tasks", json={"title": "a", "due_date": "2026-01-01"})
    client.post("/api/tasks", json={"title": "b", "due_date": "2026-02-02"})
    got = client.get("/api/tasks?date=2026-01-01").get_json()["tasks"]
    assert len(got) == 1 and got[0]["title"] == "a"


def test_oversized_request_body_rejected(client):
    payload = '{"title":"' + "x" * 1_100_000 + '"}'
    r = client.post("/api/tasks", data=payload, content_type="application/json")
    assert r.status_code == 413


def test_running_reconciled_on_restart(tmp_path):
    cfg = Config()
    cfg.data_dir = str(tmp_path)
    app1 = create_app(cfg)
    tid = app1.test_client().post("/api/tasks", json={"title": "x"}).get_json()["task"]["id"]
    stuck = app1.config["STORE"].get_task(tid)
    stuck["run_status"], stuck["status"] = "running", "doing"
    app1.config["STORE"].update_task(stuck)

    # a fresh app on the same data dir = "restart": orphaned runs are reconciled
    cfg2 = Config()
    cfg2.data_dir = str(tmp_path)
    t = create_app(cfg2).config["STORE"].get_task(tid)
    assert t["run_status"] == "aborted" and t["status"] == "review"
