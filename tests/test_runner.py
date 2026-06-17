import pytest

from taskdeck import create_app
from taskdeck.config import Config


@pytest.fixture
def echo_client(tmp_path):
    cfg = Config()
    cfg.data_dir = str(tmp_path)
    cfg.runner = "echo"
    app = create_app(cfg)
    app.testing = True
    return app.test_client()


def _new(client, **fields):
    payload = {"title": "demo"}
    payload.update(fields)
    return client.post("/api/tasks", json=payload).get_json()["task"]


def test_health_reports_runner_enabled(echo_client):
    body = echo_client.get("/api/health").get_json()
    assert body["runner"] == "echo"
    assert body["runner_enabled"] is True


def test_run_advances_to_review(echo_client):
    tid = _new(echo_client, body="do the thing")["id"]
    r = echo_client.post("/api/tasks/%d/run" % tid)
    assert r.status_code == 202
    task = r.get_json()["task"]
    assert task["run_status"] == "awaiting_review"
    assert task["status"] == "review"
    assert "echo: do the thing" in task["run"]["full_output"]


def test_complete_marks_done(echo_client):
    tid = _new(echo_client)["id"]
    echo_client.post("/api/tasks/%d/run" % tid)
    task = echo_client.post("/api/tasks/%d/complete" % tid).get_json()["task"]
    assert task["status"] == "done"
    assert task["run_status"] == "completed"


def test_abort_rejected_after_finish(echo_client):
    # echo finishes synchronously into awaiting_review, which is not running,
    # so it can no longer be aborted
    tid = _new(echo_client)["id"]
    echo_client.post("/api/tasks/%d/run" % tid)
    assert echo_client.post("/api/tasks/%d/abort" % tid).status_code == 409


def test_instruct_requires_awaiting_user(echo_client):
    tid = _new(echo_client)["id"]
    # fresh task is not awaiting user input -> 409
    r = echo_client.post("/api/tasks/%d/instruct" % tid, json={"message": "hi"})
    assert r.status_code == 409


def test_run_not_found(echo_client):
    assert echo_client.post("/api/tasks/999/run").status_code == 404


def test_unknown_runner_rejected(tmp_path):
    cfg = Config()
    cfg.data_dir = str(tmp_path)
    cfg.runner = "bogus"
    with pytest.raises(ValueError):
        create_app(cfg)


def test_complete_requires_finished_run(echo_client):
    tid = _new(echo_client)["id"]  # never run -> run_status "none"
    assert echo_client.post("/api/tasks/%d/complete" % tid).status_code == 409


def test_abort_requires_running(echo_client):
    tid = _new(echo_client)["id"]  # never run -> not abortable
    assert echo_client.post("/api/tasks/%d/abort" % tid).status_code == 409
