import pytest

from taskdeck import create_app
from taskdeck.config import Config


@pytest.fixture
def app(tmp_path):
    cfg = Config()
    cfg.data_dir = str(tmp_path)  # fresh SQLite db per test
    application = create_app(cfg)
    application.testing = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()
