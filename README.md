# TaskDeck

A small, self-hostable **Kanban TODO board** (Todo → Doing → Review → Done) with
zero external dependencies in its core, and an *optional, opt-in* agent runner that
can execute a card with an AI CLI.

> **Status: work in progress.** Built so far (steps 1–4): a Flask app factory, a
> SQLite store, the `/api/tasks` CRUD API, a vanilla-JS Kanban board UI, and an
> *experimental, opt-in* Claude CLI agent runner. The public packaging (Docker,
> CI, LICENSE, SECURITY.md) is not built yet.

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

| Variable               | Default            | Meaning                                          |
|------------------------|--------------------|--------------------------------------------------|
| `TASKDECK_HOST`        | `127.0.0.1`        | Bind address (loopback by default)               |
| `TASKDECK_PORT`        | `6090`             | HTTP port                                        |
| `TASKDECK_DATA`        | `./data`           | Directory for the SQLite database                |
| `TASKDECK_RUNNER`      | `none`             | Agent runner: `none` (off) / `claude` / `echo`   |
| `TASKDECK_TOKEN`       | _(unset)_          | If set, mutating/run requests need `X-TaskDeck-Token` |
| `CLAUDE_BIN`           | `which claude`     | Claude CLI path (runner=`claude`)                |
| `TASKDECK_RUN_CWD`     | `<data>/workspace` | Working directory the runner executes in         |
| `TASKDECK_RUN_TIMEOUT` | `600`              | Per-run timeout, seconds                         |
| `TASKDECK_RUN_MAXBYTES`| `100000`           | Cap on captured runner output                    |

### API

| Method · Path                 | Body                                          | Success            | Errors                          |
|-------------------------------|-----------------------------------------------|--------------------|---------------------------------|
| `GET /api/tasks`              | query: `date`, `project`, `status`            | `200 {tasks:[…]}`  | —                               |
| `POST /api/tasks`             | `{title, body?, project?, due_date?, tags?}`  | `201 {task}`       | `400` missing title             |
| `PUT /api/tasks/<id>`         | partial task (incl. `status` move)            | `200 {task}`       | `404`, `400` invalid status     |
| `DELETE /api/tasks/<id>`      | —                                             | `204`              | `404`                           |
| `GET /api/health`             | —                                             | `200 {status,…}`   | —                               |

## Agent runner (experimental, opt-in)

By default (`TASKDECK_RUNNER=none`) TaskDeck is a plain Kanban board and the run
endpoints (`/api/tasks/<id>/run|instruct|complete|abort`) are **not mounted** —
they return `404`. Set `TASKDECK_RUNNER=claude` to let each card be *executed* by
the Claude CLI: a card moves Todo → Doing (running) → either a `[QUESTION]` for
you to answer (`instruct`) or Review (`awaiting_review`) → Done (`complete`).

> ⚠️ **Security.** The runner launches an AI CLI that can run commands and touch
> files. It is experimental and **off by default**. When you enable it: keep the
> server on loopback, run it inside an isolated container, and scope
> `TASKDECK_RUN_CWD` to a throwaway workspace. The runner uses `shell=False` with
> an argument array, a minimal allowlisted environment, a realpath-checked working
> directory (sensitive paths refused), a hard timeout that kills the whole process
> group, and an output cap. State-changing requests are protected by an
> Origin/Referer check and an optional `TASKDECK_TOKEN`. This does **not** fully
> sandbox the agent — only run it in an environment you trust. A formal
> `SECURITY.md` ships with the public-packaging step.

The built-in `echo` runner (`TASKDECK_RUNNER=echo`) does no real work and exists
for tests/demos of the run lifecycle.

### Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## License

To be added with the public packaging step (planned: MIT).
