# webetu-resto

> Automate your **Webetu / ONOU** meal reservations so you never forget them again.

[Version française](README.md) · [MIT](LICENSE)

> ⚠️ **Unofficial project**, not affiliated with MESRS, ONOU or the Webetu app.
> It uses the same API as the mobile app, with **your own account**, under the
> **same rules** (one reservation per meal per day, 24 h in advance). Use at your
> own risk: automation may conflict with the service's terms.

## Features

- Books **breakfast, lunch and dinner** for the **next 3 days** (the app's exact
  rolling window).
- Uses **your restaurant** (`idDepot`); meals are only valid there.
- **Idempotent**: existing reservations are never duplicated.
- Guided first connection: asks for your **matricule** and **password** when missing.
- Self-hosted: your password never leaves your machine.

## How it works

The app offers a rolling **3-day window** (tomorrow, +2, +3). A **daily 00:05**
Africa/Algiers run fills that window, so tomorrow's breakfast is always more than
24 h away and the "reserve 24 h before" rule is respected.

## Quick start (Docker)

```bash
git clone https://github.com/HAROUNTOUM/webetu-resto.git
cd webetu-resto
docker compose run --rm webetu setup
docker compose up -d
```

`setup` asks for your matricule and password, verifies them, detects your
restaurant and writes `.env` (mode `600`). If `.env` has no credentials yet, any
command prompts for them on first connection (interactive terminal).

### Commands

`setup`, `test`, `status`, `reserve [--dry-run]`, `cancel <id>`, `daemon`.

## Without Docker

```bash
git clone https://github.com/HAROUNTOUM/webetu-resto.git
cd webetu-resto
python3 -m venv .venv
.venv/bin/pip install .
.venv/bin/webtu setup
.venv/bin/webtu test
.venv/bin/webtu daemon
```

See [`deploy/webetu-resto.service`](deploy/webetu-resto.service) for systemd and
[`docs/SELF-HOSTING.md`](docs/SELF-HOSTING.md) for the full guide.

### Windows, macOS, Linux

The CLI is pure Python (3.11+) and runs on all three systems; CI tests it on
Ubuntu, macOS and Windows.

```bash
pip install .            # or: pipx install .
webtu setup
```

On Windows (PowerShell) with a venv: `python -m venv .venv`, then
`.venv\Scripts\pip install .` and `.venv\Scripts\webtu setup`.

For the daily run without Docker: keep `webtu daemon` running, or let the OS
scheduler run `webtu reserve --yes` at 00:05 — cron (Linux), launchd (macOS) or
Task Scheduler (Windows).

## Configuration

See [`.env.example`](.env.example). Main variables: `WEBETU_USERNAME`,
`WEBETU_PASSWORD`, `WEBETU_RESTO_ID`,
`WEBETU_RUN_AT`, `WEBETU_BOOK_DAYS`, `WEBETU_MEALS`,
`WEBETU_CHECK_INTERVAL_MINUTES` (auto-check, default 60, 0 disables).

## Security

`.env` ignored by Git and chmod 600, no credentials in logs,
self-hosted by design.

## Development

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
pytest --cov
ruff check .
mypy src
```

## License

[MIT](LICENSE). Keep the disclaimer visible in forks.
