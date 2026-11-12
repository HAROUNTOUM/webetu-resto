# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- First-connection prompt: any command asks for matricule and password when
  `.env` has no credentials (interactive terminal only).
- Resto requests are retried (freshly signed) on intermittent 401/403.

### Removed

- Telegram bot and its `webtu bot` command, to be re-added as a separate project.

## [0.1.0] — 2026-11-12

### Added

- Reverse-engineered Webetu/ONOU client: login, student context, resto session,
  restaurant list, reservation list (paginated), booking and cancellation.
- HMAC-SHA256 request signing with exact-body semantics.
- Idempotent daily planner for the D+1..D+3 rolling window.
- Automatic restaurant resolution and per-meal validation.
- Telegram bot (French UI): status, reserve, cancel, settings (meals,
  restaurant, automatic mode), manual run, connection test, data deletion.
- Owner-only middleware; the bot ignores every other Telegram user.
- APScheduler daily job at 00:05 Africa/Algiers, startup catch-up and retries.
- CLI: `setup`, `test`, `status`, `reserve`, `cancel`, `daemon`, `bot`,
  `debug-config`, `version`.
- Docker image and Compose service, named state volume, non-root user.
- systemd unit for installations without Docker.
- Offline test suite (`pytest` + `respx`) with 80%+ core coverage.
- Documentation: French and English READMEs, API notes, self-hosting guide,
  security policy, contribution guide.

### Security

- `.env` is ignored by Git and written with mode `600`.
- No credentials, JWTs or tokens are logged; error messages stay generic.
- No public multi-user instance: self-hosting only.

[0.1.0]: https://github.com/YOUR-ACCOUNT/webetu-resto/releases/tag/v0.1.0
