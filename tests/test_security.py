from taskdeck import create_app
from taskdeck.config import Config


def _client(tmp_path, token=""):
    cfg = Config()
    cfg.data_dir = str(tmp_path)
    cfg.token = token
    app = create_app(cfg)
    app.testing = True
    return app.test_client()


def test_cross_origin_post_blocked(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/tasks", json={"title": "x"},
               headers={"Origin": "http://evil.example"})
    assert r.status_code == 403


def test_same_origin_post_allowed(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/tasks", json={"title": "x"},
               headers={"Origin": "http://localhost"})
    assert r.status_code == 201


def test_no_origin_allowed(tmp_path):
    # non-browser client (curl/tests) sends no Origin/Referer -> allowed
    assert _client(tmp_path).post("/api/tasks", json={"title": "x"}).status_code == 201


def test_safe_method_not_guarded(tmp_path):
    c = _client(tmp_path)
    r = c.get("/api/tasks", headers={"Origin": "http://evil.example"})
    assert r.status_code == 200


def test_token_required_when_set(tmp_path):
    c = _client(tmp_path, token="s3cret")
    assert c.post("/api/tasks", json={"title": "x"}).status_code == 403
    ok = c.post("/api/tasks", json={"title": "x"},
                headers={"X-TaskDeck-Token": "s3cret"})
    assert ok.status_code == 201


def test_opaque_origin_blocked(tmp_path):
    # `Origin: null` (sandboxed iframe / data: doc) must not slip past the guard
    c = _client(tmp_path)
    assert c.post("/api/tasks", json={"title": "x"},
                  headers={"Origin": "null"}).status_code == 403
