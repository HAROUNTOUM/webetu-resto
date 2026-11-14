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
24 h away and the "reserve 24 h before" rule is respected. The `daemon` runs **once a day**
at the planned time (`WEBETU_RUN_AT`), then waits for the next one (its logs say
"prochain passage prévu"); it only retries after a failure. An extra check is available
with `WEBETU_CHECK_INTERVAL_MINUTES` (off by default).

**No always-on machine?** A scheduled GitHub Actions workflow
([`.github/workflows/reserve.yml`](.github/workflows/reserve.yml), see
[`docs/SELF-HOSTING.md`](docs/SELF-HOSTING.md), option D) can run the booking for you.

## Quick start (Docker)

Requires Docker with the Compose plugin. Nothing else to install: the image bundles
Python and every dependency.

```bash
git clone https://github.com/HAROUNTOUM/webetu-resto.git
cd webetu-resto
./scripts/docker-setup.sh
```

The script checks Docker, builds the image, asks for your matricule, password and
restaurant, then starts the daily daemon. Manually:

```bash
docker compose build
docker compose run --rm webetu setup     # creates the configuration
docker compose up -d                     # starts the daily daemon
```

The configuration (`.env`) and state are created **inside the Docker volume**
`webetu-resto-state` (`/data`): no file to create on the host, and nothing in
`docker inspect`. Useful: `docker compose logs -f webetu`,
`docker compose run --rm webetu status`, `docker compose down`.

## Install `webtu` as a terminal command

Needs Python 3.11+. The script creates a dedicated virtual environment (the system Python
is untouched) and adds a `webtu` command.

```bash
# Linux / macOS
./scripts/install.sh && webtu setup
```
```powershell
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File scripts\install.ps1; webtu setup
```

Uninstall with `./scripts/install.sh --uninstall` (`-Uninstall` on Windows). Alternatives:
`pipx install .` or `uv tool install .` from the project folder.

Configuration is read from `WEBETU_ENV_FILE`, then `./.env`, then the per-user config
folder (`~/.config/webetu-resto/.env` on Linux), so `webtu` works from any directory.
`webtu debug-config` prints the file in use. Commands: `setup`, `test`, `status`,
`reserve [--dry-run]`, `cancel <id>`, `daemon`.

## Configuration

See [`.env.example`](.env.example). Main variables: `WEBETU_USERNAME`,
`WEBETU_PASSWORD`, `WEBETU_RESTO_ID`, `WEBETU_RUN_AT`, `WEBETU_BOOK_DAYS`,
`WEBETU_MEALS`, `WEBETU_CHECK_INTERVAL_MINUTES` (optional extra check, default 0 = once a day only),
`WEBETU_ENV_FILE` (explicit config file) and `WEBETU_STATE_PATH` (default:
`state.json` next to your config; `/data/state.json` in Docker).

## Security

`.env` ignored by Git and chmod 600 (Linux/macOS; on Windows it stays in your user
profile), no credentials in logs, self-hosted by design.

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
