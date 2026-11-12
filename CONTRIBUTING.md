# Contributing

Thanks for helping students not miss a meal. This is a small, pragmatic project:
small changes, clear tests, no unnecessary dependencies.

## Ground rules

- **Never commit real credentials, JWTs, tokens, APKs or decompiled bundles.**
  Tests must use synthetic values. A pull request that contains a real
  matricule, password or Telegram token will be rejected and the secret must be
  rotated.
- Be kind. See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
- Keep the API layer isolated in `src/webetu_resto/client.py`. Booking logic,
  formatting and the bot should not know raw endpoint shapes.
- Respect the service. No account creation, quota bypass, parallel account
  farming or aggressive request rates.

## Development setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/) (or plain `pip`).

```bash
git clone https://github.com/HAROUNTOUM/webetu-resto.git
cd webetu-resto
uv venv --python 3.12
uv pip install -e ".[dev]"
cp .env.example .env
chmod 600 .env
```

You do **not** need real Webetu credentials to run the tests: every HTTP call is
mocked with `respx`.

## Before opening a pull request

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov
```

CI runs the same commands on Python 3.11, 3.12 and 3.13. Coverage must stay at
or above 80% for the core modules (the CLI, scheduler and bot entry point are
excluded because they are mostly wiring).

## What to test

- Pure logic (dates, idempotency, meal mapping, depot resolution) goes in the
  matching `tests/test_*.py` file.
- New API behaviour: add a `respx` route and assert the exact payload and
  signature. Do not call the live API in tests; the `live` marker exists for
  optional manual smoke tests.
- Telegram handlers: keep network calls in `asyncio.to_thread`; do not block the
  event loop.

## Commit style

Conventional Commits, in English or French:

```
feat: add dinner-only mode
fix: do not retry after a 401
docs: document the HMAC framing
```

Keep a commit focused. If you change the API layer, explain in the body what
endpoint changed and how you verified it (without leaking account data).

## Reporting an API change

Open an issue with:

- the endpoint and the old/new response shape (redact ids and tokens);
- the date you observed it;
- whether the mobile app still works.

Do not paste a full HAR file or a proxy capture: it contains your JWT.

## License

By contributing, you agree that your contribution is licensed under the MIT
License (see [`LICENSE`](LICENSE)).
