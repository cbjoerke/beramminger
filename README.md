# Beramminger Scraper

Automatisk scraper som henter berammingsdata fra domstol.no og lagrer dem i MongoDB Atlas.

## Funksjonalitet

- Henter daglige beramminger fra domstol.no API
- Sjekker om beramminger allerede eksisterer i databasen
- Henter tilleggsinformasjon for nye beramminger
- Lagrer data i MongoDB Atlas
- Kjører automatisk hver dag kl. 20:00 UTC via GitHub Actions

## Oppsett

### 1. MongoDB Atlas

1. Opprett en MongoDB Atlas-konto på [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Opprett et cluster
3. Opprett en database bruker med lese/skrive-tilgang
4. Kopier connection string (URI)

### 2. GitHub Secrets

1. Gå til repository Settings → Secrets and variables → Actions
2. Klikk "New repository secret"
3. Navn: `MONGODB_URI`
4. Verdi: Din MongoDB Atlas connection string (f.eks. `mongodb+srv://username:password@cluster.mongodb.net/`)

### 3. Lokal Utvikling

Opprett en `.env` fil i prosjektets rotmappe:

```
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
```

Installer avhengigheter:

```bash
pip install -r pyproject.toml
# eller
uv sync
```

Kjør scriptet:

```bash
python scripts/beramminger.py
```

## GitHub Action

Workflowen er konfigurert i `.github/workflows/scraper.yml` og kjører:
- Automatisk hver dag kl. 20:00 UTC
- Manuelt via "Actions" → "Daily Beramminger Scrape" → "Run workflow"

## Avhengigheter

- pandas
- pymongo
- python-dotenv
- requests
