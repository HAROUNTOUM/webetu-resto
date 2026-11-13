# syntax=docker/dockerfile:1

# ---- build: install the package and its dependencies into a venv ----------
FROM python:3.12-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install .

# ---- runtime: only the venv, no build tools --------------------------------
FROM python:3.12-slim AS runtime

# Credentials (.env) and state live in the /data volume, created by
# `docker compose run --rm webetu setup`. Nothing has to exist on the host.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    TZ=Africa/Algiers \
    WEBETU_ENV_FILE=/data/.env \
    WEBETU_STATE_PATH=/data/state.json

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /data \
    && chown app:app /data \
    && chmod 700 /data

COPY --from=build /opt/venv /opt/venv

USER app
WORKDIR /data
VOLUME ["/data"]

ENTRYPOINT ["webtu"]
CMD ["daemon"]
