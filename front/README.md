# TrackerApp — Live Position Map (skeleton)

A Next.js (App Router) + TypeScript front end that shows a **2D floor-plan map**
with a moving dot per tracked observer, updated in real time from the
[TrackerApp Positioning API](../api_tracker_app). Each dot is a computed
position fix (`x`, `y` in meters); the fixed ESP32 scanning stations are drawn
as square markers. This is the floor-plan view the API's README says "doesn't
exist yet."

It's a **skeleton**: the map, coordinate mapping, polling, per-observer tracks
and trails are in place and runnable, but intentionally minimal.

## Quick start

```bash
cp .env.local.example .env.local   # defaults are fine for local dev
npm install
npm run dev                        # http://localhost:3000
```

Runs out of the box in **mock mode** — three simulated observers glide around
the floor — so you can see tracking without the backend up.

## Data source

The map plots position fixes, so it reads them from the backend:

| Endpoint          | Method | Status                            |
| ----------------- | ------ | --------------------------------- |
| `/health`         | GET    | ✅ implemented                    |
| `/sightings`      | POST   | ✅ implemented (ingest)           |
| `/fixes`          | POST   | ✅ implemented (ingest)           |
| `/fixes/recent`   | GET    | ✅ implemented (read side for map) |

The ESPs send raw RSSI (`POST /sightings`); the backend turns that into
positions (`POST /fixes`) and serves them back newest-first from
`GET /fixes/recent`, which this app polls.

**Mock mode** (`NEXT_PUBLIC_USE_MOCK=true`, the standalone `npm run dev`
default) still simulates moving observers so the map runs without a backend.
Set it to `false` to hit the real API — the docker-compose stack does this
automatically.

## Run with the full stack

From the parent `api_tracker_app` repo, `docker compose up --build` starts
Postgres, the API, Grafana, and this map together. The map is served on
**http://localhost:3001** (3000 is Grafana) with mock mode off.

## The floor layout is client config

The API stores raw metric coordinates but nothing about the physical room or
where the ESP stations sit — that's deployment-specific. It lives in
`src/lib/floor.ts`: edit `FLOOR` (room extent in meters) and `STATIONS` (ESP
positions) to match your real deployment.

## Configuration (`.env.local`)

| Variable                       | Default                 | Meaning                              |
| ------------------------------ | ----------------------- | ------------------------------------ |
| `NEXT_PUBLIC_API_BASE_URL`     | `http://localhost:8000` | FastAPI base URL                     |
| `NEXT_PUBLIC_POLL_INTERVAL_MS` | `1000`                  | Poll cadence (matches the dot glide) |
| `NEXT_PUBLIC_USE_MOCK`         | `true`                  | Simulate tracks instead of calling the API |

## Layout

```
src/
  app/
    page.tsx                dashboard: map + observer side panel
    layout.tsx              root layout
    globals.css             theme tokens (light + dark)
    dashboard.module.css    dashboard styles
  components/
    FloorMap.tsx            the 2D SVG map (floor, stations, dots, trails)
    FloorMap.module.css
    ObserverLegend.tsx      per-observer list with live coordinates
    StatCard.tsx            KPI tile
    HealthBadge.tsx         API liveness indicator
  hooks/
    usePolling.ts           interval polling (pauses on hidden tab)
  lib/
    types.ts                types mirroring the API payloads
    floor.ts                room + ESP station layout, observer colors
    tracks.ts               group fixes → per-observer tracks/trails
    config.ts               env-driven runtime config
    api.ts                  typed API client (marks the assumed endpoint)
    mock.ts                 simulated moving observers
```

## How the map works

- `FloorMap` renders an SVG whose viewBox is the room scaled by `PX_PER_M`.
  World meters → pixels via `toPx`, with the Y axis flipped (screen Y grows down).
- `toTracks` groups the flat fix list into one track per observer (newest =
  current dot, the rest = a fading trail polyline).
- The current-position marker is positioned with a CSS `transform` transition,
  so between polls each dot **glides** to its new spot instead of snapping.
- Each observer gets a stable color (`observerColor`); the uncertainty radius is
  drawn as a translucent halo.

## Real-time approach

The backend has no push channel (no WebSocket/SSE), so the map polls
`/fixes/recent` on an interval via `usePolling` (pausing while the tab is
hidden). Moving to SSE/WebSocket later just means replacing `usePolling` — the
map, tracks and types are unchanged.

## Next steps

- Add `GET /fixes/recent` backend-side, then turn off mock mode.
- Overlay a real floor-plan image behind the grid.
- Add an occupancy heatmap layer and per-observer position history/playback.
