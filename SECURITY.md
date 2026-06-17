# Security Policy

## Reporting a vulnerability

Please report security issues privately via GitHub Security Advisories (or email
the maintainer). Do not open public issues for sensitive reports. You can expect
an initial response within a few days.

## Threat model & safe operation

TaskDeck is a single-user, self-hosted tool. It binds to `127.0.0.1` by default
and has no authentication of its own.

### The agent runner is the main risk

With `TASKDECK_RUNNER=claude`, TaskDeck launches the Claude CLI as a subprocess,
which can run commands and modify files. This feature is **experimental and
disabled by default**. When you enable it:

- Run TaskDeck inside an isolated container or VM.
- Keep it on loopback; never expose the port to a network without an
  authenticating reverse proxy.
- Scope `TASKDECK_RUN_CWD` to a throwaway workspace directory.
- Optionally set `TASKDECK_TOKEN` to require a header on state-changing requests.

The runner inherits the server's environment (so the CLI can authenticate as it
normally would), so this is **not** a sandbox. Only enable the runner in an
environment you trust, and isolate it with a container.

### Built-in hardening

- `shell=False` with an argument array (no shell interpolation of task text)
- a realpath-checked working directory; sensitive system paths are refused
- a hard per-run timeout that terminates the whole process group (no orphans)
- a cap on captured output size
- an Origin/Referer same-origin check on `POST`/`PUT`/`DELETE` (CSRF / DNS
  rebinding), plus an optional `TASKDECK_TOKEN` gate

## Supported versions

The latest release on the default branch is supported.
