def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "TaskDeck" in html
    for status in ("todo", "doing", "review", "done"):
        assert 'data-status="%s"' % status in html


def test_static_assets(client):
    for path in ("/static/app.js", "/static/style.css"):
        assert client.get(path).status_code == 200
