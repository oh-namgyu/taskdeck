# Contributing to TaskDeck

Thanks for your interest! TaskDeck is a small, dependency-light project and
contributions are welcome.

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q          # run the test suite
python run.py                # serve at http://127.0.0.1:6090
```

The test suite needs no network or API key: the Claude runner is exercised with a
fake CLI binary.

## Guidelines

- Keep the **core** dependency-free (Flask + Python stdlib only). Optional
  features go behind a config flag, like the agent runner.
- No inline styles — add reusable classes to `taskdeck/static/style.css`.
- Add or update tests in `tests/` for any behavior change.
- Run `ruff check .` before opening a pull request.

## Pull requests

Keep PRs focused and describe what changed and how you verified it.
