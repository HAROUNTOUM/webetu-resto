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
les oublis, les redémarrages et les réservations annulées. Le `daemon` ne tourne qu'**une fois par jour**, à l'heure prévue (`WEBETU_RUN_AT`), puis
attend le passage suivant (il écrit « prochain passage prévu » dans ses logs) ; il
réessaie seulement après un échec. Une vérification supplémentaire est possible avec
`WEBETU_CHECK_INTERVAL_MINUTES` (désactivée par défaut).

**Sans machine allumée en permanence :** un workflow GitHub Actions planifié
([`.github/workflows/reserve.yml`](.github/workflows/reserve.yml), voir
[`docs/SELF-HOSTING.md`](docs/SELF-HOSTING.md), option D) peut faire le passage à ta place.

## Démarrage rapide (Docker, recommandé)

Prérequis : Docker avec le plugin Compose (`docker compose version`). Rien d'autre à
installer : l'image contient Python et toutes les dépendances.

```bash
git clone https://github.com/HAROUNTOUM/webetu-resto.git
cd webetu-resto
./scripts/docker-setup.sh
```

Le script vérifie Docker, construit l'image, te demande ton **matricule**, ton **mot de
passe** et ton **restaurant**, puis démarre le passage quotidien. Sans le script :

```bash
docker compose build
docker compose run --rm webetu setup     # crée la configuration
docker compose up -d                     # lance le passage quotidien
```

Ta configuration (`.env`) et l'état sont créés **dans le volume Docker**
`webetu-resto-state` (`/data`). Aucun fichier n'est à créer sur ta machine, et le mot de
passe n'apparaît pas dans `docker inspect`.

### Utiliser

| Commande | Effet |
|---|---|
| `docker compose logs -f webetu` | suivre les logs |
| `docker compose run --rm webetu status` | réservations des 3 prochains jours |
| `docker compose run --rm webetu reserve --dry-run` | simuler sans réserver |
| `docker compose run --rm webetu setup` | changer matricule, mot de passe ou restaurant |
| `docker compose down` | arrêter (la configuration est conservée) |

## Installer `webtu` comme commande du terminal

Python 3.11 ou plus récent est nécessaire. Le script crée un environnement virtuel dédié
(rien n'est installé dans le Python du système) et ajoute la commande `webtu`.

**Linux / macOS**

```bash
git clone https://github.com/HAROUNTOUM/webetu-resto.git
cd webetu-resto
./scripts/install.sh
webtu setup
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/HAROUNTOUM/webetu-resto.git
cd webetu-resto
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
webtu setup
```

Désinstaller : `./scripts/install.sh --uninstall` (ou `-Uninstall` sous Windows).
Alternatives : `pipx install .` ou `uv tool install .` depuis le dossier du projet.

La configuration est lue dans cet ordre : `WEBETU_ENV_FILE`, puis `.env` dans le dossier
courant, puis le dossier de configuration de ton système
(`~/.config/webetu-resto/.env` sous Linux). `webtu` fonctionne donc depuis n'importe quel
dossier ; `webtu debug-config` affiche le fichier utilisé.

Ensuite :

```bash
webtu test
webtu status
webtu daemon          # passage quotidien, à laisser tourner
```

Ou avec systemd : voir [`deploy/webetu-resto.service`](deploy/webetu-resto.service)
et le guide complet [`docs/SELF-HOSTING.md`](docs/SELF-HOSTING.md).

Le CLI est du Python pur : la CI le teste sur Ubuntu, macOS et Windows. Pour un passage
quotidien sans Docker, garde `webtu daemon` ouvert, ou programme `webtu reserve --yes` à
00:05 avec cron (Linux), launchd (macOS) ou le Planificateur de tâches (Windows).

## Configuration

Toutes les options sont dans le fichier de configuration (`.env`, voir
[`.env.example`](.env.example) ; `webtu debug-config` indique le fichier utilisé).

| Variable | Défaut | Rôle |
|---|---|---|
| `WEBETU_USERNAME` | — | matricule |
| `WEBETU_PASSWORD` | — | mot de passe |
| `WEBETU_RESTO_ID` | auto | `idDepot` du restaurant |
| `WEBETU_RUN_AT` | `00:05` | heure du passage quotidien |
| `WEBETU_BOOK_DAYS` | `1,2,3` | fenêtre glissante |
| `WEBETU_CHECK_INTERVAL_MINUTES` | `0` | vérification supplémentaire optionnelle, toutes les N minutes (0 = un seul passage par jour) |
| `WEBETU_MEALS` | `1,2,3` | 1=petit-déj, 2=déjeuner, 3=dîner |
| `WEBETU_TIMEZONE` | `Africa/Algiers` | fuseau horaire |
| `WEBETU_DRY_RUN` | `false` | simuler sans réserver |
| `WEBETU_STATE_PATH` | `<dossier de config>/state.json` | état et historique (`/data/state.json` sous Docker) |
| `WEBETU_ENV_FILE` | — | chemin explicite du fichier de configuration |

## Sécurité

- `.env` est ignoré par Git et protégé en `600` (Linux/macOS ; sous Windows, il reste dans ton profil utilisateur).
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
