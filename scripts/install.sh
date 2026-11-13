#!/usr/bin/env sh
# Install `webtu` as a command on Linux / macOS, in its own virtual environment
# (no pipx needed, nothing touches the system Python).
#
#   ./scripts/install.sh               install or upgrade
#   ./scripts/install.sh --uninstall   remove the command (config is kept)
set -eu

HERE=$(cd "$(dirname "$0")/.." && pwd)
PREFIX="${WEBETU_HOME:-$HOME/.local/share/webetu-resto}"
BIN="${WEBETU_BIN:-$HOME/.local/bin}"

fail() { printf 'Erreur : %s\n' "$1" >&2; exit 1; }

if [ "${1:-}" = "--uninstall" ]; then
  rm -f "$BIN/webtu"
  rm -rf "$PREFIX"
  echo "webtu désinstallé. Ta configuration reste dans le dossier de config de ton système (webetu-resto/) ; supprime-la à la main si tu veux."
  exit 0
fi

PYTHON=""
for candidate in python3.13 python3.12 python3.11 python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 \
     && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    PYTHON=$candidate
    break
  fi
done
[ -n "$PYTHON" ] || fail "Python 3.11 ou plus récent est requis. Installe-le (apt install python3 python3-venv / brew install python) puis relance."

echo "==> Python : $($PYTHON --version)"
mkdir -p "$PREFIX" "$BIN"
"$PYTHON" -m venv "$PREFIX/venv" 2>/dev/null \
  || fail "impossible de créer l'environnement virtuel. Sur Debian/Ubuntu : sudo apt install python3-venv"

echo "==> Installation des dépendances…"
"$PREFIX/venv/bin/python" -m pip install --quiet --upgrade pip
"$PREFIX/venv/bin/python" -m pip install --quiet --upgrade "$HERE"

ln -sf "$PREFIX/venv/bin/webtu" "$BIN/webtu"
echo "==> Commande installée : $BIN/webtu"

case ":$PATH:" in
  *":$BIN:"*) ;;
  *) printf '\nAjoute %s à ton PATH, puis rouvre le terminal :\n  echo '\''export PATH="%s:$PATH"'\'' >> ~/.profile\n' "$BIN" "$BIN" ;;
esac

printf '\nProchaine étape : webtu setup\n'
