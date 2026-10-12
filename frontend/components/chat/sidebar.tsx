import { ArrowUpRight } from "lucide-react"

import { cn } from "@/lib/utils"

export const TOPICS = [
  {
    label: "Customs & VAT",
    question: "What VAT rate applies to imports into South Africa?",
  },
  {
    label: "Delivery SLAs",
    question: "How long does delivery take from Johannesburg to Durban?",
  },
  {
    label: "Dangerous goods",
    question: "Do I need a Safety Data Sheet to ship dangerous goods?",
  },
  {
    label: "Claims & insurance",
    question: "How long do I have to report damaged goods?",
  },
  {
    label: "Cross-border docs",
    question: "What is a SADC Certificate of Origin used for?",
  },
  { label: "Pricing & fuel", question: "How is volumetric weight calculated?" },
  {
    label: "Driver safety",
    question: "How many hours can a driver drive without a break?",
  },
  {
    label: "POPIA & privacy",
    question: "Why does the chatbot log my questions?",
  },
]

export function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary font-display text-sm font-bold text-primary-foreground">
        BF
      </span>
      <span className="font-display text-lg font-bold tracking-wide uppercase">
        Baobab Freight
      </span>
    </div>
  )
}

/**
 * Topic panel: a flat sky-blue block with the topics as white pills. On desktop
 * it's a permanent side panel; on phones it's the full-screen "Topics" tab,
 * shown only while `mobileOpen` is set.
 */
export function Sidebar({
  onPickTopic,
  mobileOpen = false,
}: {
  onPickTopic: (question: string) => void
  mobileOpen?: boolean
}) {
  return (
    <aside
      className={cn(
        "relative w-full shrink-0 flex-col overflow-hidden bg-sky text-on-accent lg:flex lg:w-80 lg:rounded-3xl",
        mobileOpen ? "flex" : "hidden"
      )}
    >
      <div
        className="pointer-events-none absolute -right-16 -bottom-16 size-56 rounded-full bg-on-accent/10"
        aria-hidden="true"
      />
      <div className="relative p-6">
        <h1 className="font-display text-4xl leading-none font-bold uppercase">
          Ask about freight.
        </h1>
        <p className="mt-3 text-sm leading-relaxed font-medium text-on-accent/75">
          Customs, delivery SLAs, claims, and compliance for Baobab Freight
          &amp; Logistics, a fictional freight company. Every answer is cited.
        </p>
      </div>

      <div className="relative flex-1 overflow-y-auto px-6 pb-6">
        <div className="flex flex-col gap-1.5">
          {TOPICS.map((topic) => (
            <button
              key={topic.label}
              type="button"
              onClick={() => onPickTopic(topic.question)}
              className="group flex items-center justify-between rounded-full bg-white/70 px-4 py-2.5 text-left text-sm font-semibold transition-colors hover:bg-on-accent hover:text-white focus-visible:ring-3 focus-visible:ring-on-accent/40 focus-visible:outline-none"
            >
              {topic.label}
              <ArrowUpRight
                className="size-4 opacity-0 transition-opacity group-hover:opacity-100"
                aria-hidden="true"
              />
            </button>
          ))}
        </div>
      </div>

      <div className="relative px-6 pb-5">
        <a
          href="https://github.com/TheOneAndOnlyNjabulo/baobab-freight"
          target="_blank"
          rel="noreferrer"
          className="text-xs font-semibold underline-offset-4 hover:underline"
        >
          View source on GitHub
        </a>
      </div>
    </aside>
  )
}
