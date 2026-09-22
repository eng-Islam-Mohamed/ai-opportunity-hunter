# AI Opportunity Hunter

Evidence-first B2B opportunity intelligence. Operators define a market and the services they sell; the system discovers companies, persists provenance, identifies grounded problems, matches relevant offers, calculates transparent scores, and exports ranked leads.

## Implemented vertical slice

- FastAPI API with correlation IDs, structured logs, campaign lifecycle, lead details, and exports.
- PostgreSQL/SQLAlchemy models and Alembic migrations with server-only Supabase RLS defaults.
- Fixture discovery plus a Google Places Text Search adapter.
- Normalization, provider-ID/domain deduplication, contact and digital-asset persistence.
- SSRF-safe public-site crawler and deterministic conversion-signal parser.
- First-class evidence, grounded problem contracts, deterministic service matching, sales copy, and explainable scoring.
- Replaceable OpenRouter structured-output provider configured for DeepSeek V4 Pro.
- LangGraph campaign execution with stable thread IDs and development checkpointing.
- Idempotent CSV and Google Sheets exporters.
- Next.js 16 operator dashboard with campaign creation, ranked leads, evidence briefs, and export controls.

## Commandes pour lancer le projet

Ouvrir PowerShell dans le dossier du projet :

```powershell
cd "C:\Users\ASUS TUF GAMING 15\Desktop\B2B bussiness scraper"
```

### 1. Lancer le backend API

Dans un premier terminal PowerShell :

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps/api --reload --host 127.0.0.1 --port 8000
```

Verifier que l'API marche :

```text
http://127.0.0.1:8000/health
```

Si tout est bon, la reponse doit etre :

```json
{"status":"ok"}
```

### 2. Lancer le frontend

Dans un deuxieme terminal PowerShell :

```powershell
cd "C:\Users\ASUS TUF GAMING 15\Desktop\B2B bussiness scraper\apps\web"
pnpm dev
```

Ensuite ouvrir l'application ici :

```text
http://127.0.0.1:3000
```

### 3. Lancer backend + frontend avec une seule commande

Depuis le dossier principal du projet :

```powershell
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m uvicorn app.main:app --app-dir apps/api --reload --host 127.0.0.1 --port 8000" -WorkingDirectory "C:\Users\ASUS TUF GAMING 15\Desktop\B2B bussiness scraper"; Start-Process -FilePath "cmd.exe" -ArgumentList "/c pnpm dev" -WorkingDirectory "C:\Users\ASUS TUF GAMING 15\Desktop\B2B bussiness scraper\apps\web"
```

### Notes importantes

- Il faut garder les deux serveurs ouverts pendant l'utilisation.
- Le backend tourne sur `http://127.0.0.1:8000`.
- Le frontend tourne sur `http://127.0.0.1:3000`.
- Le bouton `Send to Sheets` utilise la connexion Google deja configuree.
- Pour eviter une grande consommation Google Places, commencer les tests avec `10`, `25` ou `50` resultats.

## Setup local complet

1. Copy `.env.example` to `.env`; never put secrets in frontend environment variables.
2. Start PostgreSQL: `docker compose up -d db`.
3. Create a Python 3.12+ virtual environment and run `pip install -e ".[dev]"`.
4. Apply migrations: `alembic upgrade head`.
5. Start the API: `uvicorn app.main:app --app-dir apps/api --reload`.
6. In `apps/web`, run `pnpm install && pnpm dev`.
7. Open `http://localhost:3000`; API documentation is at `http://localhost:8000/docs`.

For a database-free demo, set `DATABASE_URL=sqlite+aiosqlite:///./dev.db` before migrating and running the API. Production remains PostgreSQL.

## Provider activation

- Fixture-safe mode is the default and performs no paid discovery or LLM analysis.
- Set `DISCOVERY_PROVIDER=google_places` and provide `GOOGLE_MAPS_API_KEY` for live discovery.
- Set `ENABLE_LLM_ANALYSIS=true`, `LLM_PROVIDER=openrouter`, and `LLM_API_KEY` for DeepSeek analysis.
- For Google Sheets export, this project can use OAuth via `GOOGLE_OAUTH_CLIENT_SECRETS_FILE` and `GOOGLE_OAUTH_TOKEN_FILE`, or a service account if your Google Cloud organization allows service account keys.

Google Places and Sheets usage must be reviewed against current provider policies before production launch. Outreach remains human-controlled.
