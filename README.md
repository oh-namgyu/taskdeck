# TaskDeck

A small, self-hostable **Kanban TODO board** (Todo → Doing → Review → Done) with
zero external dependencies in its core, and an *optional, opt-in* agent runner that
can execute a card with an AI CLI.

> **Status: work in progress.** Built so far (steps 1–2): a Flask app factory, a
> SQLite store, the `/api/tasks` CRUD API, and a vanilla-JS Kanban board UI. The
> agent runner plugin and the public packaging (Docker, CI, LICENSE, SECURITY) are
> not built yet.

## What works now

- **Stack:** Python (>=3.9) + Flask, storage via stdlib `sqlite3`, no-build
  vanilla-JS frontend.
- **Kanban board:** 4 columns (Todo / Doing / Review / Done) with add, edit,
  delete, column moves, project/date filters, and a done-count badge.
- **No private infrastructure:** configuration is entirely environment-driven; no
  hardcoded paths or external services.

### Run

```bash
pip install -r requirements.txt
python run.py            # board UI + API on http://127.0.0.1:6090
```

Open <http://127.0.0.1:6090> for the board; the JSON API lives under `/api`.

### Configuration (environment variables)

| Variable          | Default       | Meaning                                  |
|-------------------|---------------|------------------------------------------|
| `TASKDECK_HOST`   | `127.0.0.1`   | Bind address (loopback by default)       |
| `TASKDECK_PORT`   | `6090`        | HTTP port                                |
| `TASKDECK_DATA`   | `./data`      | Directory for the SQLite database        |
| `TASKDECK_RUNNER` | `none`        | Agent runner; `none` keeps run API off   |

### API

| Method · Path                 | Body                                          | Success            | Errors                          |
|-------------------------------|-----------------------------------------------|--------------------|---------------------------------|
| `GET /api/tasks`              | query: `date`, `project`, `status`            | `200 {tasks:[…]}`  | —                               |
| `POST /api/tasks`             | `{title, body?, project?, due_date?, tags?}`  | `201 {task}`       | `400` missing title             |
| `PUT /api/tasks/<id>`         | partial task (incl. `status` move)            | `200 {task}`       | `404`, `400` invalid status     |
| `DELETE /api/tasks/<id>`      | —                                             | `204`              | `404`                           |
| `GET /api/health`             | —                                             | `200 {status,…}`   | —                               |

Run endpoints (`/api/tasks/<id>/run` …) are **not mounted** while
`TASKDECK_RUNNER=none`, so they return `404` until the runner plugin lands.

### Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## License

To be added with the public packaging step (planned: MIT).
