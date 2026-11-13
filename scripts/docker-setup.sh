#!/usr/bin/env sh
# One-shot Docker setup: checks Docker, builds the image, asks for your
# matricule/password/restaurant, then starts the daily daemon.
set -eu
cd "$(dirname "$0")/.."

fail() { printf 'Erreur : %s\n' "$1" >&2; exit 1; }

command -v docker >/dev/null 2>&1 \
  || fail "Docker n'est pas installé. Installe-le : https://docs.docker.com/get-docker/"
docker compose version >/dev/null 2>&1 \
  || fail "le plugin « docker compose » est introuvable (Docker 20.10+ / Compose v2)."
docker info >/dev/null 2>&1 \
  || fail "le démon Docker ne répond pas. Démarre Docker puis relance ce script."

echo "==> Construction de l'image…"
docker compose build

echo "==> Configuration (matricule, mot de passe, restaurant)…"
docker compose run --rm webetu setup

echo "==> Démarrage du passage quotidien…"
docker compose up -d

cat <<'MSG'

C'est prêt. Commandes utiles :
  docker compose logs -f webetu                 suivre les logs
  docker compose run --rm webetu status         voir les 3 prochains jours
  docker compose run --rm webetu reserve --dry-run
  docker compose down                           arrêter (la config est conservée)
MSG
