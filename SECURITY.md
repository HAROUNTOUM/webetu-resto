# Security policy

## What this project handles

- Your Webetu **matricule and password** (used to obtain a short-lived JWT).
- A local **state file** with your meal preferences and the date of the last run.
- Short-lived JWTs held in memory only.

It does **not** collect telemetry, analytics, crash reports or usage data, and it
does not talk to any server other than the Webetu/ONOU endpoints.

## Self-hosted by design

There is no public multi-user instance. You run the process yourself, so you are
the only person who holds your credentials.

## Protecting your secrets

1. Keep `.env` readable only by you:

   ```bash
   chmod 600 .env
   ```

   `webtu setup` does this automatically. The file is listed in `.gitignore`;
   verify with `git check-ignore -v .env` before your first commit.

2. Never paste `.env`, a JWT, a QR code or a screenshot containing your token
   into an issue, a chat or a pull request.

3. Do not reuse your Webetu password on other services. If it leaks, change it
   in the Webetu app and run `webtu setup` again.

4. Run the Docker container as a non-root user (the provided image already uses
   uid 1000) and keep the host patched.

5. The state file contains no password and no JWT, but it does reveal your meal
   preferences and restaurant. Protect it like any other personal file.

## Logging

The client never logs request bodies, query strings, passwords, JWTs or tokens. Errors include only the HTTP method, the endpoint path and a
server message. If you add logging while contributing, keep that rule.

## Reporting a vulnerability

Please **do not open a public issue** for a vulnerability that could expose
credentials or allow someone else to act on another user's account.

Use GitHub's private vulnerability reporting:
**Security → Advisories → Report a vulnerability** on the repository.

Include:

- affected version or commit;
- a minimal reproduction (no real credentials);
- impact and suggested fix, if you have one.

You can expect an acknowledgement within a few days. This is a volunteer
project, so no bounty is offered.

## Scope

In scope:

- credential or token leakage in logs, errors, state or Docker layers;
- command injection, path traversal or unsafe file writes;
- dependency vulnerabilities with a realistic exploit path.

Out of scope:

- the Webetu/ONOU service itself (report it to the operator, not here);
- account bans or terms-of-service consequences;
- rate limits or API changes (open a normal issue);
- findings that require a modified local build or physical access.

## If you exposed a secret by accident

1. Change your Webetu password immediately.
2. Remove the secret from the current files and from Git history
   (`git filter-repo`), then force-push the cleaned history.
3. Assume the secret is compromised even if the commit was short-lived.
