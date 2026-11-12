# webetu-resto

> Automatise tes réservations de repas **Webetu / ONOU** et ne les oublie plus.

[English version](README.en.md) · [MIT](LICENSE)

> ⚠️ **Projet non officiel**, sans affiliation avec le MESRS, l'ONOU ou l'application
> Webetu. Il utilise la même API que l'application mobile, avec **ton propre compte**
> et dans les **mêmes règles** (une réservation par repas et par jour, 24 h avant).
> Utilisation à tes risques : une automatisation peut être contraire aux conditions
> d'utilisation du service.

## Ce que ça fait

- Réserve automatiquement **le petit-déjeuner, le déjeuner et le dîner** pour les
  **3 prochains jours** (la fenêtre exacte de l'application).
- Choisit **ton restaurant** (`idDepot`) : sans ça, le repas n'est pas valable.
- **Idempotent** : ne double jamais une réservation existante.
- Première connexion guidée : le tool te demande ton **matricule** et ton **mot de passe**.
- Tourne chez toi (VPS, Raspberry Pi, vieux PC) : **personne d'autre ne détient ton mot de passe**.

## Comment ça marche

L'application Webetu ouvre les réservations sur une fenêtre glissante de **3 jours**
(demain, +2, +3). Un passage **chaque jour à 00:05** (heure d'Alger) remplit cette
fenêtre et garde toujours une longueur d'avance. À cette heure-là, le petit-déjeuner
de demain est à plus de 24 h, donc la règle « réserver 24 h avant » est respectée.

```
aujourd'hui        demain        +2            +3
  00:05      →      réservé      réservé       réservé
```

Un passage quotidien est plus fiable qu'un passage « tous les 3 jours » : il rattrape
les oublis, les redémarrages et les réservations annulées.

## Démarrage rapide (Docker, recommandé)

### 1. Installer

```bash
git clone https://github.com/TON-COMPTE/webetu-resto.git
cd webetu-resto
docker compose run --rm webetu setup
docker compose up -d
```

`setup` demande ton matricule et ton mot de passe Webetu, vérifie la connexion,
détecte ton restaurant et écrit `.env` (permissions `600`). L'état est conservé dans
le volume Docker `webetu-resto-state` ; les logs et les sauvegardes sont dans
[`docs/SELF-HOSTING.md`](docs/SELF-HOSTING.md).

### 2. Utiliser

| Commande | Effet |
|---|---|
| `webtu setup` | saisir matricule, mot de passe, restaurant |
| `webtu test` | vérifier la connexion (aucune réservation) |
| `webtu status` | réservations des 3 prochains jours |
| `webtu reserve --dry-run` | simuler sans réserver |
| `webtu reserve` | réserver les repas manquants |
| `webtu cancel <id>` | annuler une réservation |
| `webtu daemon` | passage quotidien automatique à 00:05 |

Si `.env` ne contient pas encore tes identifiants, n'importe quelle commande te les
demande à la première connexion (terminal interactif).

## Installation sans Docker

```bash
git clone https://github.com/TON-COMPTE/webetu-resto.git
cd webetu-resto
python3 -m venv .venv
.venv/bin/pip install .
.venv/bin/webtu setup
.venv/bin/webtu test
.venv/bin/webtu status
.venv/bin/webtu daemon
```

Ou avec systemd : voir [`deploy/webetu-resto.service`](deploy/webetu-resto.service)
et le guide complet [`docs/SELF-HOSTING.md`](docs/SELF-HOSTING.md).

### Windows, macOS, Linux

Le CLI est du Python pur (3.11+) et tourne sur les trois systèmes ; la CI le teste
sur Ubuntu, macOS et Windows.

```bash
pip install .            # ou : pipx install .
webtu setup
```

Sous Windows (PowerShell), avec un venv : `python -m venv .venv`, puis
`.venv\Scripts\pip install .` et `.venv\Scripts\webtu setup`.

Pour le passage quotidien sans Docker : `webtu daemon` (laisser tourner), ou le
planificateur du système qui lance `webtu reserve --yes` à 00:05 — cron (Linux),
launchd (macOS) ou Planificateur de tâches (Windows).

## Configuration

Toutes les options sont dans `.env` (voir [`.env.example`](.env.example)).

| Variable | Défaut | Rôle |
|---|---|---|
| `WEBETU_USERNAME` | — | matricule |
| `WEBETU_PASSWORD` | — | mot de passe |
| `WEBETU_RESTO_ID` | auto | `idDepot` du restaurant |
| `WEBETU_RUN_AT` | `00:05` | heure du passage quotidien |
| `WEBETU_BOOK_DAYS` | `1,2,3` | fenêtre glissante |
| `WEBETU_MEALS` | `1,2,3` | 1=petit-déj, 2=déjeuner, 3=dîner |
| `WEBETU_TIMEZONE` | `Africa/Algiers` | fuseau horaire |
| `WEBETU_DRY_RUN` | `false` | simuler sans réserver |
| `WEBETU_STATE_PATH` | `./data/state.json` | préférences et historique |

## Sécurité

- `.env` est ignoré par Git et protégé en `600`.
- Aucun mot de passe, JWT ou token n'est journalisé.
- Le modèle **self-host** signifie que tu es le seul dépositaire de tes identifiants.
- Ne partage jamais ton `.env` et ne publie pas de capture avec tes identifiants.

## FAQ

**Pourquoi pas une réservation tous les 3 jours ?**
La fenêtre est glissante : si tu rates un passage, il manque des repas. Un passage
quotidien idempotent comble les trous.

**Et si le daemon redémarre ?**
Au démarrage, il vérifie le dernier passage et rattrape immédiatement si nécessaire.

**Le restaurant est-il automatique ?**
Oui quand un seul `isRu=1` existe. Sinon `webtu setup --change-resto` permet de le choisir. Un repas
réservé dans un autre restaurant n'est pas consommable.

**L'API change ?**
Les endpoints sont documentés dans [`docs/API-NOTES.md`](docs/API-NOTES.md) et le
client est isolé dans `src/webetu_resto/client.py`. Les tests utilisent des réponses
enregistrées, pas le vrai serveur.

**Mon compte peut-il être bloqué ?**
Le tool respecte les règles du serveur (pas de contournement de quota, pas de comptes
multiples). Il reste non officiel : à utiliser en connaissance de cause.

## Développement

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
pytest --cov
ruff check .
mypy src
```

Voir [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

[MIT](LICENSE) — fais-en bon usage, et garde le disclaimer visible dans les forks.
