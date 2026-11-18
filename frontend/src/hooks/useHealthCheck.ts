"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { HealthStatus, TracingStatus } from "../lib/types";
import { api } from "../lib/api";

interface HealthState {
  connected: boolean;
  containerRunning: boolean;
  tracing: TracingStatus | null;
  loading: boolean;
}

const POLL_INTERVAL = 30_000;
const RETRY_INTERVAL = 5_000;

/**
 * Polls /health and /tracing endpoints.
 * Auto-retries faster when disconnected.
 */
export function useHealthCheck() {
  const [state, setState] = useState<HealthState>({
    connected: false,
    containerRunning: false,
    tracing: null,
    loading: true,
  });

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const check = useCallback(async () => {
    let connected = false;
    let containerRunning = false;
    let tracing: TracingStatus | null = null;

    try {
      const health = await api.health();
      connected = true;
      containerRunning = health.container_running;
    } catch {
      connected = false;
    }

    if (connected) {
      try {
        tracing = await api.tracing();
      } catch {
        tracing = null;
      }
    }

    setState({ connected, containerRunning, tracing, loading: false });

    // Schedule next check — faster retry when disconnected
    const delay = connected ? POLL_INTERVAL : RETRY_INTERVAL;
    timerRef.current = setTimeout(check, delay);
  }, []);

  useEffect(() => {
    check();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [check]);

  return state;
}