import { ThemeToggle } from "@/components/chat/theme-toggle"

export const TOPICS = [
  { label: "Customs & VAT", question: "What VAT rate applies to imports into South Africa?" },
  { label: "Delivery SLAs", question: "How long does delivery take from Johannesburg to Durban?" },
  { label: "Dangerous goods", question: "Do I need a Safety Data Sheet to ship dangerous goods?" },
  { label: "Claims & insurance", question: "How long do I have to report damaged goods?" },
  { label: "Cross-border docs", question: "What is a SADC Certificate of Origin used for?" },
  { label: "Pricing & fuel", question: "How is volumetric weight calculated?" },
  { label: "Driver safety", question: "How many hours can a driver drive without a break?" },
  { label: "POPIA & privacy", question: "Why does the chatbot log my questions?" },
]

export function Brand() {
  return (
    <div className="flex items-center gap-2">
      <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary font-display text-sm font-bold text-primary-foreground">
        BF
      </span>
      <span className="font-display text-base font-bold tracking-wide uppercase">
        Baobab Freight
      </span>
    </div>
  )
}

export function Sidebar({ onPickTopic }: { onPickTopic: (question: string) => void }) {
  return (
    <aside className="hidden w-72 shrink-0 flex-col border-r border-border lg:flex">
      <div className="border-b border-border p-5">
        <Brand />
        <p className="mt-3 text-sm text-muted-foreground">
          Ask about customs, delivery SLAs, claims, and compliance for Baobab Freight & Logistics,
          a fictional freight company.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        <h2 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          Ask about
        </h2>
        <div className="mt-3 flex flex-col gap-1.5">
          {TOPICS.map((topic) => (
            <button
              key={topic.label}
              type="button"
              onClick={() => onPickTopic(topic.question)}
              className="rounded-md px-2.5 py-1.5 text-left text-sm text-foreground/80 transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              {topic.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-border p-3">
        <a
          href="https://github.com/TheOneAndOnlyNjabulo/baobab-freight"
          target="_blank"
          rel="noreferrer"
          className="px-2 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          View source
        </a>
        <ThemeToggle />
      </div>
    </aside>
  )
}
