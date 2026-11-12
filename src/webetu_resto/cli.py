"""`webtu` command line interface."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import typer
from pydantic import ValidationError
from rich.console import Console

from . import __version__
from .booking import resolve_depot, target_dates
from .client import WebetuClient
from .config import Settings, parse_days
from .errors import ConfigError, WebetuError
from .formatting import (
    format_day,
    format_depots,
    format_last_run,
    format_report,
    format_snapshot,
)
from .log import configure_logging
from .meals import parse_meals
from .runner import fetch_snapshot, options_from_settings, run_with_prefs
from .state import StateStore

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Automatise les réservations de repas Webetu / ONOU.",
)
console = Console()


def _configure_stdio() -> None:
    """Emit UTF-8 everywhere (legacy Windows consoles default to cp1252/cp850)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                continue


@app.callback()
def _main() -> None:
    _configure_stdio()


def _load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        raise ConfigError(
            "configuration invalide dans .env (vérifie WEBETU_RUN_AT, WEBETU_MEALS, "
            "WEBETU_BOOK_DAYS et WEBETU_TIMEZONE)"
        ) from exc


def _configure_logging(settings: Settings) -> None:
    configure_logging(settings.webetu_log_level)


def _today(settings: Settings) -> date:
    return datetime.now(settings.timezone).date()


def _state(settings: Settings) -> StateStore:
    return StateStore(settings.webetu_state_path)


def _client(settings: Settings) -> WebetuClient:
    return WebetuClient(
        settings.webetu_username,
        settings.password,
        progres_base=settings.webetu_progres_base,
        resto_base=settings.webetu_resto_base,
        hmac_secret=settings.hmac_secret,
        request_interval=settings.webetu_request_interval,
    )


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ConfigError(f"date invalide: {value!r} (format AAAA-MM-JJ)") from exc


def _env_quote(value: str) -> str:
    if any(character in value for character in " #'\"\t"):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _write_env(path: Path, values: dict[str, str]) -> None:
    """Merge values into .env, preserving comments and unrelated keys."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(values)
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                output.append(f"{key}={_env_quote(remaining.pop(key))}")
                continue
        output.append(line)
    if output and output[-1].strip():
        output.append("")
    if not path.exists():
        output.append("# Généré par `webtu setup` — ne jamais committer ce fichier.")
    for key, value in remaining.items():
        output.append(f"{key}={_env_quote(value)}")
    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    path.chmod(0o600)


def _choose_depot(settings: Settings, depots: list[Any], *, force: bool = False) -> Any:
    if settings.webetu_resto_id is not None and not force:
        for depot in depots:
            if depot.id == settings.webetu_resto_id:
                return depot
    try:
        return resolve_depot(depots, None)
    except ConfigError:
        console.print(format_depots(depots))
        choice = typer.prompt("Numéro du restaurant", type=int)
        if not 1 <= choice <= len(depots):
            raise ConfigError("choix de restaurant invalide") from None
        return depots[choice - 1]


def _run_setup(current: Settings, *, change_resto: bool = False) -> None:
    """Ask for matricule + password, verify them, pick a restaurant, write .env."""
    username = typer.prompt("Matricule Webetu", default=current.webetu_username or "")
    if not username.strip():
        raise ConfigError("le matricule est obligatoire")
    username = username.strip()
    password_input = typer.prompt(
        "Mot de passe Webetu (laisser vide pour conserver l'actuel)"
        if current.password
        else "Mot de passe Webetu",
        hide_input=True,
        default="",
        show_default=False,
    )
    password = password_input or current.password
    if not password:
        raise ConfigError("le mot de passe est obligatoire")

    console.print("[dim]Vérification des identifiants…[/dim]")
    probe = WebetuClient(
        username,
        password,
        progres_base=current.webetu_progres_base,
        resto_base=current.webetu_resto_base,
        hmac_secret=current.hmac_secret,
        request_interval=current.webetu_request_interval,
    )
    try:
        probe.login()
        context = probe.load_student_context()
        probe.ensure_resto_session()
        depots = probe.get_depots()
    finally:
        probe.close()

    if not depots:
        raise ConfigError("aucun restaurant renvoyé par l'API")
    depot = _choose_depot(current, depots, force=change_resto)
    console.print(
        f"[green]Connecté :[/green] {username} — "
        f"{context.residence_name or 'résidence inconnue'} — {depot.label}"
    )

    env_path = Path(".env")
    _write_env(
        env_path,
        {
            "WEBETU_USERNAME": username,
            "WEBETU_PASSWORD": password,
            "WEBETU_RESTO_ID": str(depot.id),
        },
    )
    console.print(f"[green]Configuration écrite dans {env_path} (chmod 600).[/green]")


def _is_interactive() -> bool:
    return sys.stdin.isatty()


def _ensure_credentials(settings: Settings) -> Settings:
    """Return settings with credentials, prompting on first connection if needed."""
    if settings.webetu_username.strip() and settings.password:
        return settings
    if not _is_interactive():
        settings.require_credentials()
        return settings
    console.print(
        "[bold]Première connexion[/bold] — saisis ton matricule et ton mot de passe Webetu."
    )
    _run_setup(settings)
    reloaded = _load_settings()
    reloaded.require_credentials()
    return reloaded


@app.command()
def setup(
    change_resto: bool = typer.Option(
        False, "--change-resto", help="Forcer le choix du restaurant."
    ),
) -> None:
    """Assistant interactif : matricule, mot de passe, restaurant."""
    try:
        current = _load_settings()
        _configure_logging(current)
        _run_setup(current, change_resto=change_resto)
        console.print("\nProchaines étapes :")
        console.print("  webtu test                 # vérifier la connexion")
        console.print("  webtu status               # voir les 3 prochains jours")
        console.print("  webtu reserve --dry-run    # simuler une réservation")
    except WebetuError as exc:
        console.print(f"[red]Erreur :[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command()
def test() -> None:
    """Vérifie les identifiants et l'accès au restaurant (aucune réservation)."""
    try:
        settings = _load_settings()
        _configure_logging(settings)
        settings = _ensure_credentials(settings)
        state = _state(settings)
        snapshot = fetch_snapshot(
            options_from_settings(
                settings,
                resto_id=state.load().prefs.resto_id or settings.webetu_resto_id,
            )
        )
        console.print(
            f"[green]OK[/green] — {snapshot.context.username} — "
            f"{snapshot.context.residence_name or 'résidence'} — {snapshot.depot.label}"
        )
    except WebetuError as exc:
        console.print(f"[red]Erreur :[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command()
def status(
    as_json: bool = typer.Option(False, "--json", help="Sortie JSON."),
) -> None:
    """Affiche les réservations des 3 prochains jours."""
    try:
        settings = _load_settings()
        _configure_logging(settings)
        settings = _ensure_credentials(settings)
        state = _state(settings)
        stored = state.load()
        options = options_from_settings(
            settings,
            resto_id=stored.prefs.resto_id or settings.webetu_resto_id,
        )
        snapshot = fetch_snapshot(options)
        days = target_dates(_today(settings), settings.book_days)
        meals = stored.prefs.meals or settings.meals

        if as_json:
            payload = {
                "username": snapshot.context.username,
                "year": snapshot.context.year_code,
                "wilaya": snapshot.context.wilaya,
                "residence": snapshot.context.residence_name,
                "depot": {
                    "id": snapshot.depot.id,
                    "name": snapshot.depot.display_name,
                },
                "days": [day.isoformat() for day in days],
                "reservations": [
                    {
                        "id": reservation.id,
                        "date": reservation.day.isoformat(),
                        "meal": reservation.label,
                        "depot": reservation.depot_fr,
                        "candelete": reservation.candelete,
                    }
                    for reservation in snapshot.reservations
                    if reservation.day in days
                ],
            }
            console.print_json(json.dumps(payload, ensure_ascii=False))
            return

        console.print(format_snapshot(snapshot, days, meals))
        console.print("")
        console.print(format_last_run(stored))
    except WebetuError as exc:
        console.print(f"[red]Erreur :[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command()
def reserve(
    day: str | None = typer.Option(None, "--date", "-d", help="Date exacte AAAA-MM-JJ."),
    days: str | None = typer.Option(
        None, "--days", help="Fenêtre glissante, ex. 1,2,3 (défaut .env)."
    ),
    meals: str | None = typer.Option(
        None, "--meals", help="Repas: 1=f petit-déj, 2=déjeuner, 3=dîner."
    ),
    resto: int | None = typer.Option(None, "--resto", help="idDepot à utiliser."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Afficher sans réserver."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Ne pas demander confirmation."),
) -> None:
    """Réserve les repas manquants pour une date ou la fenêtre glissante."""
    try:
        settings = _load_settings()
        _configure_logging(settings)
        settings = _ensure_credentials(settings)
        state = _state(settings)
        stored = state.load()

        target_days: list[date] | None = None
        if day is not None:
            target_days = [_parse_date(day)]
        elif days is not None:
            offsets = parse_days(days)
        else:
            offsets = settings.book_days
        if target_days is None:
            target_days = target_dates(_today(settings), offsets)

        selected_meals = (
            parse_meals(meals) if meals is not None else (stored.prefs.meals or settings.meals)
        )
        selected_resto = (
            resto if resto is not None else (stored.prefs.resto_id or settings.webetu_resto_id)
        )

        if not dry_run and not yes:
            console.print("Date(s) : " + ", ".join(format_day(item) for item in target_days))
            console.print("Repas   : " + ", ".join(str(meal) for meal in selected_meals))
            console.print(f"Resto   : {selected_resto or 'auto'}")
            if not typer.confirm("Confirmer la réservation ?", default=True):
                console.print("Annulé.")
                raise typer.Exit(0)

        report = run_with_prefs(
            settings,
            state,
            target_days=target_days,
            dry_run=dry_run,
            meals=selected_meals,
            resto_id=selected_resto,
        )
        console.print(format_report(report))
        if report.failed:
            raise typer.Exit(1)
    except WebetuError as exc:
        console.print(f"[red]Erreur :[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command()
def cancel(
    reservation_id: int = typer.Argument(..., help="Identifiant de la réservation."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Ne pas demander confirmation."),
) -> None:
    """Annule une réservation annulable."""
    try:
        settings = _load_settings()
        _configure_logging(settings)
        settings = _ensure_credentials(settings)
        state = _state(settings)
        stored = state.load()
        options = options_from_settings(
            settings,
            resto_id=stored.prefs.resto_id or settings.webetu_resto_id,
        )
        snapshot = fetch_snapshot(options)
        reservation = next(
            (item for item in snapshot.reservations if item.id == reservation_id), None
        )
        if reservation is None:
            raise ConfigError(f"réservation {reservation_id} introuvable")
        if not reservation.candelete:
            raise ConfigError(
                f"la réservation {reservation_id} n'est pas annulable "
                "(déjà consommée ou trop proche)"
            )
        console.print(
            f"{reservation.id} — {format_day(reservation.day)} — "
            f"{reservation.label} — {reservation.depot_fr}"
        )
        if not yes and not typer.confirm("Annuler cette réservation ?", default=False):
            console.print("Annulé.")
            raise typer.Exit(0)

        client = _client(settings)
        try:
            client.login()
            client.load_student_context()
            client.ensure_resto_session()
            result = client.cancel(reservation_id)
        finally:
            client.close()
        message = result.get("message") if isinstance(result, dict) else None
        console.print(f"[green]Annulation envoyée.[/green] {message or ''}".strip())
    except WebetuError as exc:
        console.print(f"[red]Erreur :[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command()
def daemon() -> None:
    """Lance la planification quotidienne (cron/systemd friendly)."""
    try:
        settings = _load_settings()
        _configure_logging(settings)
        settings = _ensure_credentials(settings)
        from .scheduler import run_cli_daemon

        run_cli_daemon(settings, _state(settings))
    except WebetuError as exc:
        console.print(f"[red]Erreur :[/red] {exc}")
        raise typer.Exit(1) from exc


@app.command()
def version() -> None:
    """Affiche la version."""
    console.print(f"webetu-resto {__version__}")


@app.command("debug-config")
def debug_config() -> None:
    """Affiche la configuration sans aucun secret."""
    try:
        settings = _load_settings()
        console.print_json(json.dumps(settings.describe(), ensure_ascii=False))
    except WebetuError as exc:
        console.print(f"[red]Erreur :[/red] {exc}")
        raise typer.Exit(1) from exc
