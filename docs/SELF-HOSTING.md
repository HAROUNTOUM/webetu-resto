# Self-hosting guide

The long-running process is `webtu daemon`, which contains the daily scheduler.
The CLI (`webtu status`, `webtu reserve`, ...) is available in the same container
or installation.

## Option A — Docker Compose (recommended)

### Requirements

- Docker Engine 24+ with the Compose plugin;
- a host that stays online around 00:05 Africa/Algiers (a small VPS, a
  Raspberry Pi or a home server is enough).

### Install

```bash
git clone https://github.com/HAROUNTOUM/webetu-resto.git
cd webetu-resto
./scripts/docker-setup.sh        # build + setup + start, with Docker checks
```

or step by step:

```bash
docker compose build
docker compose run --rm webetu setup
docker compose up -d
docker compose logs -f webetu
```

`setup` verifies the login, the student context, the resto session and the
restaurant **before** writing the config. It asks for your matricule and
password (hidden input). The config file is created **inside the `/data`
volume** (`/data/.env`, mode `600`), so no file has to exist on the host and
there is no uid/permission problem. Credentials are not passed through the
container environment, so `docker inspect` does not show them.

To read or edit it:

```bash
docker run --rm -v webetu-resto-state:/data alpine cat /data/.env
```

### What runs

- one container, `webetu-resto`, running `webtu daemon`;
- it embeds an APScheduler daily job at `WEBETU_RUN_AT`
  (00:05 by default);
- a catch-up run starts 10 seconds after boot when today's pass is missing or
  failed;
- config and state are stored in the named volume `webetu-resto-state`, at
  `/data/.env` and `/data/state.json`.

### Day-to-day commands

```bash
docker compose logs -f webetu          # follow logs
docker compose restart webetu          # restart
docker compose run --rm webetu status  # read-only status
docker compose run --rm webetu test    # connection check
docker compose run --rm webetu reserve --dry-run
docker compose down                 # stop (state is kept)
git pull && docker compose build && docker compose up -d   # update
```

### Backup and restore

```bash
# backup
docker run --rm -v webetu-resto-state:/data -v "$PWD":/backup alpine \
  tar czf /backup/webetu-state.tgz -C /data .

# restore
docker run --rm -v webetu-resto-state:/data -v "$PWD":/backup alpine \
  tar xzf /backup/webetu-state.tgz -C /data
```

The state file has no password and no JWT. It is still personal data (meal
preferences, restaurant, chat id); store backups accordingly.

### Timezone

The container ships `tzdata` and sets `TZ=Africa/Algiers`. Algeria does not use
daylight saving time. If you change `WEBETU_TIMEZONE`, also change `TZ` in
`docker-compose.yml` so log timestamps match.

## Option B — systemd without Docker

```bash
sudo useradd --system --create-home --home-dir /opt/webetu-resto webetu
sudo -u webetu git clone https://github.com/HAROUNTOUM/webetu-resto.git /opt/webetu-resto
cd /opt/webetu-resto
sudo -u webetu python3 -m venv .venv
sudo -u webetu .venv/bin/pip install .
sudo -u webetu env WEBETU_ENV_FILE=/opt/webetu-resto/.env .venv/bin/webtu setup
sudo install -m 644 deploy/webetu-resto.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now webetu-resto
sudo journalctl -u webetu-resto -f
```

The provided unit assumes:

- the code and `.env` live in `/opt/webetu-resto`;
- the service user is `webetu`;
- only `/opt/webetu-resto/data` needs to be writable.

Adapt `User`, `WorkingDirectory`, the `Environment=` paths and `ReadWritePaths` if your
paths differ. The unit runs `webtu daemon`; the output goes to the journal.

## Option C — cron instead of the built-in scheduler

If you prefer cron, do not run `webtu daemon`; schedule a
one-shot pass instead:

```cron
5 0 * * * cd /opt/webetu-resto && .venv/bin/webtu reserve --yes >> data/cron.log 2>&1
```

Use `--yes` only in a non-interactive context. The command is idempotent: a
second pass on the same day books nothing new.

## Option D — GitHub Actions (no computer needed)

Run the booking on GitHub's servers so it works even when your own machine is
off for days.

1. Create a **private** repository and push this project to it.
2. In *Settings → Secrets and variables → Actions*, add the secrets
   `WEBETU_USERNAME`, `WEBETU_PASSWORD` and `WEBETU_RESTO_ID`.
3. The workflow [`.github/workflows/reserve.yml`](../.github/workflows/reserve.yml)
   runs at 00:05 and 06:05 Algiers time. Without the secrets it is skipped.
4. Test it once: *Actions → Daily reservation → Run workflow* (tick `dry_run` to
   simulate). A failed run emails you.

Notes: GitHub's servers are outside Algeria, so check that the first manual run
succeeds. Scheduled runs can start 10–30 minutes late, which is harmless because
tomorrow's breakfast is still more than 24 hours away at 00:05. Keep the
repository private: public workflow logs are visible to everyone.

## Configuration reference

| Variable | Default | Meaning |
|---|---|---|
| `WEBETU_USERNAME` | — | Webetu matricule |
| `WEBETU_PASSWORD` | — | Webetu password |
| `WEBETU_RESTO_ID` | auto | restaurant `idDepot` |
| `WEBETU_TIMEZONE` | `Africa/Algiers` | IANA timezone |
| `WEBETU_RUN_AT` | `00:05` | daily run time (`HH:MM`) |
| `WEBETU_BOOK_DAYS` | `1,2,3` | rolling window (1–3 only) |
| `WEBETU_CHECK_INTERVAL_MINUTES` | `60` | auto-check: re-run the idempotent pass to fill gaps (0 = off) |
| `WEBETU_MEALS` | `1,2,3` | 1 breakfast, 2 lunch, 3 dinner |
| `WEBETU_STATE_PATH` | `<config folder>/state.json` | runtime state (`/data/state.json` in Docker) |
| `WEBETU_DRY_RUN` | `false` | plan without booking |
| `WEBETU_MAX_RETRIES` | `2` | retries after a failed pass |
| `WEBETU_RETRY_DELAY` | `20` | base retry delay, seconds |
| `WEBETU_REQUEST_INTERVAL` | `0.3` | pause between HTTP calls |
| `WEBETU_LOG_LEVEL` | `INFO` | Python log level |

The same values can be given as environment variables; in Docker, the container
reads them from the mounted `/app/.env` file. No credential is placed in the
container environment.

## CLI reference

```text
webtu setup [--change-resto]                interactive configuration
webtu test                                  login + restaurant check, no booking
webtu status [--json]                       next 3 days and last run
webtu reserve [--date D] [--days 1,2,3] [--meals 1,2,3] [--resto ID]
             [--dry-run] [--yes]
webtu cancel RESERVATION_ID [--yes]         cancel a cancellable reservation
webtu daemon                                daily scheduler
webtu debug-config                          safe configuration dump
webtu version
```

## Troubleshooting

### `401 Unauthenticated` from the resto API

The resto service needs `POST /api/loginpwebetu` before any other call. The
client does it automatically; if you see this error, the JWT may have expired
or the password changed. Run `webtu test`.

### `aucune demande d'hébergement trouvée`

The account has no housing request for the current academic year, or the year
id changed. Check the Webetu app first. This tool only books meals for students
who have a residence.

### `plusieurs restaurants possibles`

Auto-detection only works when exactly one `isRu=1` restaurant is returned.
Choose one:

```bash
webtu setup --change-resto
# or
webtu reserve --resto 68
```

Set `WEBETU_RESTO_ID=68` in `.env` to make it permanent. The meal is only valid
in the chosen restaurant.

### The container cannot write `.env`

The image runs as uid 1000. If your host user has another uid, either run setup
on the host with `uv`/`pip`, or fix ownership:

```bash
sudo chown "$(id -u):$(id -g)" .env
```

### A run failed and the window has a hole

The daily pass is idempotent; simply run it again:

```bash
docker compose run --rm webetu reserve --yes
```

The booking window is D+1..D+3 and the server enforces 24 hours before the meal.
A meal whose 24-hour deadline has passed cannot be recovered.
