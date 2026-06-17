"""Entry point: `python run.py` (or `flask --app run run`)."""
from taskdeck import create_app

app = create_app()

if __name__ == "__main__":
    cfg = app.config["TASKDECK"]
    app.run(host=cfg.host, port=cfg.port)
