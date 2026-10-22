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

### `GET /fixes/recent`

Read side for the web map — the most recent fixes, newest first.

```
GET /fixes/recent?limit=200   # limit 1..1000, default 200
```

```json
[
  {
    "id": 42,
    "observerID": "B7E2F910",
    "x": 1.84,
    "y": -0.62,
    "uncertaintyMeters": 0.31,
    "recordedAt": "2026-01-01T12:00:00Z",
    "receivedAt": "2026-01-01T12:00:00.040Z"
  }
]
```

The `front/` web app polls this and groups rows by `observerID` into per-device
tracks (newest row = current dot, the rest = a trail). CORS is open by default
for local dev — set `CORS_ORIGINS` to the real frontend origin in production.

### `GET /health`

Plain liveness check, `{"status": "ok"}`.

## Deploying to Railway

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

> ⚠️ **Not verified against a real Grafana instance.** The `$VARIABLE` environment-variable
> expansion in `datasource.yml` is documented Grafana behavior, but Docker wasn't running while
> this was written, so it was never actually started and checked. If the datasource doesn't show
> up provisioned after deploying, check the Grafana container logs first.

## Known gaps / next steps

- **No auth** on the ingestion endpoints yet — anyone who can reach the API can write rows. Fine
  for local testing, not for anything public — this matters more once it's actually deployed to
  Railway with a real internet-reachable domain.
- **`baseURL` on the iOS side currently points at a dev-machine LAN IP**
  (`PositioningAPIClient.swift`) — update it to the Railway-generated API domain once that's
  deployed; the LAN IP only works while the phone and the Mac running `docker compose` are on the
  same network.
- **No migrations** — tables are created with `Base.metadata.create_all()` on startup. Fine while
  the schema is still moving; switch to Alembic once it stabilizes.
- **No Grafana dashboards committed yet** — `grafana/provisioning/dashboards/` is set up to receive
  dashboard JSON exports once some exist, but none have been built.
- **The floor-plan map web app now has a skeleton** — it lives in `front/` (Next.js + TypeScript),
  reads positions from `GET /fixes/recent`, and renders a live 2D map with a moving dot per
  observer. `docker compose up` builds and serves it on http://localhost:3001. Still a skeleton:
  no real floor-plan image behind the grid and no occupancy heatmap layer yet. Grafana's panels
  aren't a good fit for that specific visualization (see the iOS repo's README for why).
