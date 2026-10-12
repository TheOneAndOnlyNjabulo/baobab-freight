"use client"

import * as React from "react"

/**
 * The backend runs on a free hosting tier that sleeps after ~15 minutes idle and
 * takes up to a minute to wake. Pinging /health as soon as the page opens starts
 * that wake-up while the visitor is still reading, instead of on their first
 * question. /health is not rate limited, so this costs the visitor nothing.
 *
 * Deliberately not a keep-alive: there's no interval ping, only a re-check when
 * the tab becomes visible again after a long gap - an open tab shouldn't hold the
 * instance awake indefinitely and burn the free tier's monthly hours.
 */
export type BackendStatus = "checking" | "waking" | "ready" | "unreachable"

const API_URL = process.env.NEXT_PUBLIC_API_URL

// Only call it "waking" if the first ping is still pending after this long, so a
// warm backend never flashes the banner.
const SLOW_AFTER_MS = 3000
const ATTEMPT_TIMEOUT_MS = 65000
const RETRY_DELAY_MS = 5000
// While spinning up, the host may hang the request or fail it without CORS
// headers (a bare TypeError in the browser) - that's still "waking", not "down".
const GIVE_UP_AFTER_MS = 180000
const RECHECK_AFTER_IDLE_MS = 10 * 60 * 1000

export function useBackendStatus(): BackendStatus {
  const [status, setStatus] = React.useState<BackendStatus>("checking")

  React.useEffect(() => {
    if (!API_URL) return

    let cancelled = false
    let running = false
    let lastOkAt = 0

    async function wake() {
      if (running) return
      running = true
      const startedAt = Date.now()
      const slowTimer = setTimeout(() => {
        if (!cancelled) setStatus("waking")
      }, SLOW_AFTER_MS)

      try {
        while (!cancelled) {
          const controller = new AbortController()
          const attemptTimer = setTimeout(
            () => controller.abort(),
            ATTEMPT_TIMEOUT_MS
          )
          try {
            const response = await fetch(`${API_URL}/health`, {
              signal: controller.signal,
              cache: "no-store",
            })
            if (response.ok) {
              lastOkAt = Date.now()
              if (!cancelled) setStatus("ready")
              return
            }
          } catch {
            // Still waking - retry below.
          } finally {
            clearTimeout(attemptTimer)
          }

          if (Date.now() - startedAt > GIVE_UP_AFTER_MS) {
            if (!cancelled) setStatus("unreachable")
            return
          }
          await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS))
        }
      } finally {
        clearTimeout(slowTimer)
        running = false
      }
    }

    function handleVisibilityChange() {
      if (
        document.visibilityState === "visible" &&
        Date.now() - lastOkAt > RECHECK_AFTER_IDLE_MS
      ) {
        wake()
      }
    }

    wake()
    document.addEventListener("visibilitychange", handleVisibilityChange)
    return () => {
      cancelled = true
      document.removeEventListener("visibilitychange", handleVisibilityChange)
    }
  }, [])

  return status
}
