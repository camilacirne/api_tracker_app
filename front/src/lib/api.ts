/**
 * Typed client for the TrackerApp Positioning API.
 *
 * Endpoint status against the current backend (api_tracker_app):
 *   GET  /health            → IMPLEMENTED
 *   POST /sightings         → IMPLEMENTED (ingestion only)
 *   POST /fixes             → IMPLEMENTED (ingestion only)
 *   GET  /sightings/recent  → ASSUMED / NOT YET ON BACKEND
 *   GET  /fixes/recent      → ASSUMED / NOT YET ON BACKEND
 *   GET  /stats             → ASSUMED / NOT YET ON BACKEND
 *
 * The *Assumed* read endpoints are what a monitoring dashboard needs. They
 * don't exist yet (the README says Grafana reads Postgres directly and the
 * read-side web app "doesn't exist yet"). When mock mode is on the dashboard
 * never calls them; when it's off they'll be hit and must be added server-side.
 */

import { config } from "./config";
import { mockFixes, mockSightings, mockStats } from "./mock";
import type { Fix, Health, IngestionStats, Sighting } from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${config.apiBaseUrl}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      cache: "no-store",
    });
  } catch (cause) {
    throw new ApiError(`Network error reaching ${path}: ${String(cause)}`);
  }
  if (!res.ok) {
    throw new ApiError(`${path} responded ${res.status}`, res.status);
  }
  return (await res.json()) as T;
}

export const api = {
  /** Liveness check — the one GET endpoint that really exists today. */
  health(): Promise<Health> {
    if (config.useMock) return Promise.resolve({ status: "ok" });
    return request<Health>("/health");
  },

  /** Recent sightings. ASSUMED endpoint — served from mock until it exists. */
  recentSightings(limit = 50): Promise<Sighting[]> {
    if (config.useMock) return Promise.resolve(mockSightings(limit));
    return request<Sighting[]>(`/sightings/recent?limit=${limit}`);
  },

  /** Recent fixes. ASSUMED endpoint — served from mock until it exists. */
  recentFixes(limit = 200): Promise<Fix[]> {
    if (config.useMock) return Promise.resolve(mockFixes());
    return request<Fix[]>(`/fixes/recent?limit=${limit}`);
  },

  /** Aggregate stats. ASSUMED endpoint — derived from mock until it exists. */
  async stats(): Promise<IngestionStats> {
    if (config.useMock) {
      return mockStats(mockFixes());
    }
    return request<IngestionStats>("/stats");
  },
};
