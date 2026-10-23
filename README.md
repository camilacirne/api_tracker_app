# Positioning API

Ingestion API for the TrackerApp indoor positioning feature: receives BLE sighting and
computed-position reports from the iOS app (eventually Android, and an ESP32 acting as a fixed
scanning station too), stores them in Postgres, and exposes that data to Grafana for dashboards
(peak hours, anchor coverage) and to a future web app for the floor-plan heatmap.

This repo is backend only — no frontend of any kind lives here, including the floor-plan heatmap
itself (see "Known gaps" below).

## Stack

- **FastAPI** (Python) — the two ingestion endpoints.
- **Postgres** — storage.
- **Grafana** — reads Postgres directly (not through the API) for time-based dashboards. Comes
  pre-provisioned with the Postgres datasource (`grafana/provisioning/datasources/datasource.yml`)
  — no manual setup needed, just add dashboards.

## Running it

```bash
docker compose up --build
```

- API: http://localhost:8000 (docs at http://localhost:8000/docs)
- Grafana: http://localhost:3000 (user `admin` / password `admin`, change it on first login)
- Postgres: localhost:5432 (user/password/db: `postgres`/`postgres`/`positioning`)

## Endpoints

Payload shapes mirror exactly what `PositioningAPIClient.swift` (in the iOS app) encodes — field
names are camelCase to match Swift's default `JSONEncoder` output, not Python convention.

### `POST /sightings`

One row per anchor a phone currently sees, batched. Mirrors `[PositioningReport]`.

```json
[
  {
    "observerID": "B7E2F910",
    "anchorID": "9F3C1A02",
    "rssi": -58,
    "seenAt": "2026-01-01T12:00:00Z"
  }
]
```

`distanceMeters` is accepted (the iOS app still sends it) but **always ignored** — the server
recomputes it from `rssi` via `app/path_loss.py`, the same log-distance formula as the iOS app's
`PathLossModel.swift`. This is so there's one canonical formula instead of one per client as more
of them show up (an ESP32 sending raw RSSI over Wi-Fi is the reason this changed — firmware
shouldn't have to replicate the math). `observerID` doesn't have to be a real `BeaconID` — any
short string identifying the sender works, so a fixed ESP32 station can use its own id here.

### `POST /fixes`

The observer's own computed position for that refresh cycle. Mirrors `ObserverFixReport`. This is
the one that matters for a heatmap or an occupancy count ("how many distinct `observerID`s were
seen in this area recently") — `/sightings` alone doesn't carry a computed position.

```json
{
  "observerID": "B7E2F910",
  "x": 1.84,
  "y": -0.62,
  "uncertaintyMeters": 0.31,
  "recordedAt": "2026-01-01T12:00:00Z"
}
```

### `GET /health`

Plain liveness check, `{"status": "ok"}`.

## Deploying to Render

Switched from Railway to Render after Railway started showing "Limited Access — Deploys have
been paused due to an upstream issue" across *all* services in the project at once (including
ones that had been running fine, and the Postgres instance, which isn't even GitHub-connected) —
that pattern means it wasn't anything misconfigured on our end, so rather than wait on an
unexplained outage, we moved. The Railway steps are kept below for reference/rollback, but Render
is the one actually in use.

Three separate Render services, same shape as before: a managed Postgres, and two Docker-based
Web Services built from this one repo (API from the root `Dockerfile`, Grafana from
`grafana/Dockerfile`).

1. **Postgres** — New → PostgreSQL. Render provisions it and shows connection details (host,
   port, user, password, database name, and a ready-made `Internal Database URL`) on its page
   once created.
2. **API** — New → Web Service → connect this repo. Render auto-detects the root `Dockerfile`.
   Set `DATABASE_URL` to the Postgres service's **Internal Database URL**, with `+psycopg` added
   to the scheme (same adjustment as Railway — Render's is `postgresql://...`, this code needs
   `postgresql+psycopg://...`). Render gives the service a public `onrender.com` URL automatically
   — that's what `PositioningAPIClient.swift` (iOS) should point at.
3. **Grafana** — New → Web Service → connect this repo *again*. Render builds from a Dockerfile
   it finds via **Root Directory**/**Dockerfile Path** in the service's settings — point it at
   `grafana` (exact field layout may differ from what's described here; Render separates "build
   context directory" from "Dockerfile path" rather than having one combined "Root Directory"
   like Railway, so this may need adjusting once the actual form is visible). Environment
   variables, reading the same values off the Postgres service's page as step 2:
   - `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
   - `POSTGRES_SSLMODE=require`
   - `GF_SECURITY_ADMIN_USER`/`GF_SECURITY_ADMIN_PASSWORD` — not `admin`/`admin`, this is
     reachable from the public internet once Render assigns it a domain.

> ✅ **The `$VARIABLE` expansion in `datasource.yml` was confirmed working** — verified on a real
> deployment (Railway, before the outage): `GET /api/datasources` showed the Postgres datasource
> provisioned with the env var values correctly substituted, and `GET
> /api/datasources/uid/.../health` returned `"Database Connection OK"`. This part of the setup is
> known-good; it doesn't depend on which host runs the containers.

> ⚠️ **Render's free tier has real limits worth knowing before relying on this**: free web
> services spin down after a period of inactivity and take ~30-60s to wake up on the next
> request (the API and Grafana will feel "slow" on the first hit after a while); free Postgres
> instances are deleted after a time limit (historically 30-90 days, but check Render's current
> terms — this changes). Fine for a class project's testing/demo use, not for anything meant to
> keep data indefinitely without upgrading.

## Deploying to Railway (previous — kept for reference)

Three separate Railway services in one project — Railway doesn't run `docker-compose.yml`
directly, each piece is added individually.

1. **Postgres** — in the Railway project, "+ New" → "Database" → "Add PostgreSQL". Railway
   provisions and manages it (including the persistent volume) — no docker-compose equivalent
   needed here.
2. **API** — "+ New" → "GitHub Repo" → this repo. Railway detects the root `Dockerfile`
   automatically. Set the `DATABASE_URL` environment variable to Railway's Postgres connection
   string, but **add `+psycopg` to the scheme** — Railway's variable is `postgresql://...`, this
   code needs `postgresql+psycopg://...` (reference the Postgres service's variable, then edit the
   scheme, rather than retyping the whole URL). Under Settings → Networking, generate a public
   domain — that's the URL `PositioningAPIClient.swift` (iOS) should point at instead of the LAN
   IP placeholder.
3. **Grafana** — "+ New" → "GitHub Repo" → this repo again, but set the service's **Root
   Directory** to `grafana` so it builds `grafana/Dockerfile` (which bakes the provisioning files
   from `grafana/provisioning` into the image — Railway can't bind-mount a volume from the repo
   the way local `docker compose` does) instead of the API's Dockerfile. Set these environment
   variables, pointing at the same Postgres service as the API:
   - `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` —
     reference them from the Postgres service's own variables.
   - `POSTGRES_SSLMODE=require` (Railway's Postgres expects TLS; the local default is `disable`).
   - `GF_SECURITY_ADMIN_USER`/`GF_SECURITY_ADMIN_PASSWORD` — **set these to something other than
     `admin`/`admin` here.** Unlike local `docker compose`, this Grafana is reachable from the
     public internet once you generate a domain for it — leaving the default credentials would let
     anyone who finds the URL into it.
   - Also generate a public domain for this service (Settings → Networking) if you want to open
     dashboards without `docker compose up` running locally.

## Known gaps / next steps

- **No auth** on the ingestion endpoints yet — anyone who can reach the API can write rows. Fine
  for local testing, not for anything public — this matters more once it's actually deployed to
  Railway with a real internet-reachable domain.
- **`baseURL` on the iOS side needs updating once more** (`PositioningAPIClient.swift`) — it was
  pointed at the Railway domain; once the Render API service has its own `onrender.com` domain,
  that's what it should point at instead.
- **No migrations** — tables are created with `Base.metadata.create_all()` on startup. Fine while
  the schema is still moving; switch to Alembic once it stabilizes.
- **No Grafana dashboards committed yet** — `grafana/provisioning/dashboards/` is set up to receive
  dashboard JSON exports once some exist, but none have been built.
- **The actual floor-plan heatmap web app doesn't exist yet** — Grafana's panels aren't a good fit
  for that specific visualization (see the iOS repo's README for why); it needs its own small
  frontend reading from this same Postgres.
