"use client";

import { useCallback, useMemo } from "react";
import styles from "./dashboard.module.css";
import { FloorMap } from "@/components/FloorMap";
import { HealthBadge } from "@/components/HealthBadge";
import { ObserverLegend } from "@/components/ObserverLegend";
import { StatCard } from "@/components/StatCard";
import { usePolling } from "@/hooks/usePolling";
import { api } from "@/lib/api";
import { config } from "@/lib/config";
import { toTracks } from "@/lib/tracks";

export default function DashboardPage() {
  const health = usePolling(useCallback(() => api.health(), []), config.pollIntervalMs);
  const fixes = usePolling(
    useCallback(() => api.recentFixes(), []),
    config.pollIntervalMs,
  );

  const tracks = useMemo(() => toTracks(fixes.data ?? []), [fixes.data]);

  const healthStatus = health.error
    ? "down"
    : health.data?.status === "ok"
      ? "ok"
      : "unknown";

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>TrackerApp — Live Position Map</h1>
          <p className={styles.subtitle}>
            Tracking observer positions from <span className={styles.mono}>/fixes</span>, polling{" "}
            <span className={styles.mono}>{config.apiBaseUrl}</span> every{" "}
            {(config.pollIntervalMs / 1000).toFixed(1)}s
          </p>
        </div>
        <div className={styles.meta}>
          <HealthBadge status={healthStatus} />
          <span>
            Updated {fixes.lastUpdated ? fixes.lastUpdated.toLocaleTimeString() : "—"}
            {fixes.refreshing ? " · ↻" : ""}
          </span>
          <button
            className={styles.button}
            onClick={() => {
              health.refresh();
              fixes.refresh();
            }}
          >
            Refresh
          </button>
        </div>
      </header>

      {config.useMock ? (
        <div className={styles.banner}>
          <strong>Mock mode.</strong> The API can&apos;t be read yet (ingestion-only:
          only <span className={styles.mono}>/health</span>,{" "}
          <span className={styles.mono}>POST /sightings</span>,{" "}
          <span className={styles.mono}>POST /fixes</span>). The dots below are
          simulated tracks. Add <span className={styles.mono}>GET /fixes/recent</span>{" "}
          on the backend, then set{" "}
          <span className={styles.mono}>NEXT_PUBLIC_USE_MOCK=false</span>.
        </div>
      ) : null}

      {fixes.error ? (
        <div className={styles.errorBanner}>
          Can&apos;t load positions: {fixes.error.message}
        </div>
      ) : null}

      <section className={styles.mapLayout}>
        <div className={styles.card}>
          <FloorMap tracks={tracks} />
        </div>

        <div className={styles.side}>
          <section className={styles.statStack}>
            <StatCard label="Tracked observers" value={tracks.length} />
            <StatCard
              label="Position fixes"
              value={fixes.data?.length ?? "—"}
              hint="in current window"
            />
          </section>
          <div className={styles.card}>
            <div className={styles.panelHead}>
              <h2 className={styles.panelTitle}>Observers</h2>
            </div>
            <ObserverLegend tracks={tracks} />
          </div>
        </div>
      </section>
    </main>
  );
}
