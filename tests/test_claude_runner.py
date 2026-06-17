import stat
import time

import pytest

from taskdeck import create_app
from taskdeck.config import Config

# Fake `claude` binaries: deterministic stand-ins so the subprocess machinery
# (spawn, parse, timeout, kill, conversation) is tested without the real CLI.
FAKE_OK = "#!/usr/bin/env python3\nprint('did the work')\n"
FAKE_QUESTION = (
    "#!/usr/bin/env python3\n"
    "print('thinking...')\n"
    "print('[QUESTION] which color?')\n"
)
FAKE_SLOW = "#!/usr/bin/env python3\nimport time\ntime.sleep(30)\n"
# Emits a question on the first call, then completes once 'convo_done' exists in
# the working directory (the runner's fixed run_cwd persists between calls).
FAKE_CONVO = (
    "#!/usr/bin/env python3\n"
    "import os\n"
    "if os.path.exists('convo_done'):\n"
    "    print('finished after your answer')\n"
    "else:\n"
    "    open('convo_done', 'w').close()\n"
    "    print('[QUESTION] more info?')\n"
)


def _fake(tmp_path, body):
    p = tmp_path / "fakeclaude"
    p.write_text(body)
    p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return str(p)


def _app(tmp_path, bin_path, timeout=30):
    cfg = Config()
    cfg.data_dir = str(tmp_path / "data")
    cfg.runner = "claude"
    cfg.claude_bin = bin_path
    cfg.run_cwd = str(tmp_path / "ws")
    cfg.run_timeout = timeout
    app = create_app(cfg)
    app.testing = True
    return app


def _create(client):
    return client.post(
        "/api/tasks", json={"title": "demo", "body": "do it"}
    ).get_json()["task"]


def _wait(store, task_id, timeout=12):
    end = time.time() + timeout
    while time.time() < end:
        t = store.get_task(task_id)
        if t and t["run_status"] != "running":
            return t
        time.sleep(0.05)
    raise AssertionError("runner did not settle: %r" % (store.get_task(task_id),))


def test_run_completes_to_review(tmp_path):
    app = _app(tmp_path, _fake(tmp_path, FAKE_OK))
    client = app.test_client()
    tid = _create(client)["id"]
    assert client.post("/api/tasks/%d/run" % tid).status_code == 202
    t = _wait(app.config["STORE"], tid)
    assert t["run_status"] == "awaiting_review"
    assert t["status"] == "review"
    assert "did the work" in t["run"]["full_output"]


def test_run_question_awaits_user(tmp_path):
    app = _app(tmp_path, _fake(tmp_path, FAKE_QUESTION))
    client = app.test_client()
    tid = _create(client)["id"]
    client.post("/api/tasks/%d/run" % tid)
    t = _wait(app.config["STORE"], tid)
    assert t["run_status"] == "awaiting_user"
    assert t["status"] == "doing"
    assert t["run"]["question"] == "which color?"


def test_timeout_marks_failed(tmp_path):
    app = _app(tmp_path, _fake(tmp_path, FAKE_SLOW), timeout=1)
    client = app.test_client()
    tid = _create(client)["id"]
    client.post("/api/tasks/%d/run" % tid)
    t = _wait(app.config["STORE"], tid, timeout=15)
    assert t["run_status"] == "failed"


def test_abort_running(tmp_path):
    app = _app(tmp_path, _fake(tmp_path, FAKE_SLOW))
    client = app.test_client()
    tid = _create(client)["id"]
    client.post("/api/tasks/%d/run" % tid)
    time.sleep(0.4)  # let the subprocess register
    t = client.post("/api/tasks/%d/abort" % tid).get_json()["task"]
    assert t["run_status"] == "aborted"
    # abort wins: the worker thread must not overwrite it back to review
    time.sleep(0.5)
    assert app.config["STORE"].get_task(tid)["run_status"] == "aborted"


def test_instruct_after_question(tmp_path):
    app = _app(tmp_path, _fake(tmp_path, FAKE_CONVO))
    client = app.test_client()
    store = app.config["STORE"]
    tid = _create(client)["id"]
    client.post("/api/tasks/%d/run" % tid)
    assert _wait(store, tid)["run_status"] == "awaiting_user"
    r = client.post("/api/tasks/%d/instruct" % tid, json={"message": "blue"})
    assert r.status_code == 200
    t = _wait(store, tid)
    assert t["run_status"] == "awaiting_review"
    assert "finished after your answer" in t["run"]["full_output"]


def test_rerun_allowed_after_abort(tmp_path):
    # aborting a running task must not brick it: a fresh run is still accepted
    app = _app(tmp_path, _fake(tmp_path, FAKE_SLOW))
    client = app.test_client()
    store = app.config["STORE"]
    tid = _create(client)["id"]
    client.post("/api/tasks/%d/run" % tid)
    time.sleep(0.4)
    assert client.post("/api/tasks/%d/abort" % tid).get_json()["task"]["run_status"] == "aborted"
    # re-run is accepted (not stuck at 409) and the abort is not resurrected
    assert client.post("/api/tasks/%d/run" % tid).status_code == 202
    time.sleep(0.3)
    assert store.get_task(tid)["run_status"] == "running"
    client.post("/api/tasks/%d/abort" % tid)  # cleanup


def test_sensitive_run_cwd_rejected(tmp_path):
    cfg = Config()
    cfg.data_dir = str(tmp_path)
    cfg.runner = "claude"
    cfg.run_cwd = "/etc"
    with pytest.raises(Exception):
        create_app(cfg)
