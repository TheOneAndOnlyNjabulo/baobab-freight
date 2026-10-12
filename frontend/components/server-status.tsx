"use client"

import * as React from "react"
import { Loader2 } from "lucide-react"

import type { BackendStatus } from "@/hooks/use-backend-status"

export function ServerStatusBanner({ status }: { status: BackendStatus }) {
  if (status === "waking") {
    return (
      <div
        role="status"
        className="flex items-start gap-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-800 dark:text-amber-200"
      >
        <Loader2
          className="mt-0.5 size-4 shrink-0 animate-spin"
          aria-hidden="true"
        />
        <div>
          <p className="font-medium">Waking up the demo server…</p>
          <p className="mt-0.5 text-amber-800/80 dark:text-amber-200/80">
            It runs on free hosting that sleeps when idle, so the first request
            after a quiet spell can take up to a minute. Pick a topic or type
            your question in the meantime.
          </p>
        </div>
      </div>
    )
  }

  if (status === "unreachable") {
    return (
      <div
        role="alert"
        className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
      >
        Can&apos;t reach the demo server right now. Please try again in a few
        minutes.
      </div>
    )
  }

  return null
}

/**
 * Mount only while a request is pending - it starts hidden on every mount, so
 * there's no state to reset between requests. Covers the case the health check
 * can't: a page left open long enough for the server to fall asleep again.
 */
export function SlowRequestHint({ delayMs = 7000 }: { delayMs?: number }) {
  const [visible, setVisible] = React.useState(false)

  React.useEffect(() => {
    const timer = setTimeout(() => setVisible(true), delayMs)
    return () => clearTimeout(timer)
  }, [delayMs])

  if (!visible) return null

  return (
    <p className="animate-message-in text-xs text-muted-foreground">
      Still working… if the demo server was asleep, this first request can take
      up to a minute.
    </p>
  )
}
