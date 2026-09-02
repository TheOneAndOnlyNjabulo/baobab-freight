"use client"

import * as React from "react"
import { Send } from "lucide-react"
import ReactMarkdown from "react-markdown"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ThemeToggle } from "@/components/chat/theme-toggle"
import type { ChatMessage } from "@/lib/chat-types"
import { ChatApiError, sendChatMessage } from "@/lib/api"
import { cn } from "@/lib/utils"

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: "seed-1",
    role: "assistant",
    content:
      "Hi, I'm the Baobab Freight Assistant. Ask me about customs, delivery SLAs, dangerous goods, claims, or any of our other policies.",
  },
]

// Optimistic starting value shown before the first real response - the backend
// is the source of truth for the actual count (RATE_LIMIT_PER_IP in main.py),
// this just avoids showing nothing on first load. Corrected immediately once a
// real remaining_questions comes back.
const INITIAL_REMAINING_GUESS = 10

function nextId() {
  return Math.random().toString(36).slice(2)
}

export function ChatInterface() {
  const [messages, setMessages] = React.useState<ChatMessage[]>(INITIAL_MESSAGES)
  const [input, setInput] = React.useState("")
  const [remaining, setRemaining] = React.useState(INITIAL_REMAINING_GUESS)
  const [isSending, setIsSending] = React.useState(false)
  const scrollRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [messages, isSending])

  const limitReached = remaining <= 0
  const canSend = input.trim().length > 0 && !isSending && !limitReached

  async function handleSend() {
    if (!canSend) return

    const question = input.trim()
    setMessages((prev) => [...prev, { id: nextId(), role: "user", content: question }])
    setInput("")
    setIsSending(true)

    try {
      const result = await sendChatMessage(question)
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: "assistant", content: result.answer, sources: result.sources },
      ])
      setRemaining(result.remaining_questions)
    } catch (err) {
      if (err instanceof ChatApiError && err.status === 429) {
        setRemaining(0)
      }
      const message = err instanceof ChatApiError ? err.message : "Something went wrong. Please try again."
      setMessages((prev) => [...prev, { id: nextId(), role: "error", content: message }])
    } finally {
      setIsSending(false)
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="relative flex h-svh flex-col">
      <div className="atmosphere" aria-hidden="true" />

      <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b border-border/70 px-4 py-4">
          <div>
            <div className="flex items-center gap-2">
              <span
                className="size-2 rounded-full bg-primary animate-status-pulse"
                aria-hidden="true"
              />
              <h1 className="font-display text-2xl font-bold tracking-wide text-glow uppercase">
                Baobab Freight
              </h1>
            </div>
            <p className="mt-0.5 pl-4 text-xs text-muted-foreground">
              Ask about customs, SLAs, claims, and compliance for Baobab Freight & Logistics.
            </p>
          </div>
          <ThemeToggle />
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-5">
          <div className="flex flex-col gap-4">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isSending && <TypingIndicator />}
          </div>
        </div>

        <div className="border-t border-border/70 px-4 py-3">
          <RemainingIndicator remaining={remaining} limitReached={limitReached} />
          <div className="flex items-center gap-2">
            <Input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={limitReached ? "No questions remaining" : "Ask a question..."}
              disabled={isSending || limitReached}
              aria-label="Your question"
              className="transition-shadow focus-visible:shadow-glow-sm"
            />
            <Button
              onClick={handleSend}
              disabled={!canSend}
              size="icon"
              aria-label="Send"
              className={cn(
                "shrink-0 transition-all",
                canSend && "shadow-glow-sm hover:shadow-glow hover:-translate-y-0.5"
              )}
            >
              <Send className="size-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

function RemainingIndicator({ remaining, limitReached }: { remaining: number; limitReached: boolean }) {
  const dotColor = limitReached
    ? "bg-destructive"
    : remaining <= 3
      ? "bg-amber-500"
      : "bg-primary"

  return (
    <div className="mb-2 flex items-center gap-1.5 font-mono text-[11px] tracking-wide text-muted-foreground uppercase">
      <span className={cn("size-1.5 rounded-full", dotColor)} aria-hidden="true" />
      {limitReached
        ? "Session limit reached"
        : `${remaining} question${remaining === 1 ? "" : "s"} remaining`}
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "error") {
    return (
      <div className="flex flex-col items-start animate-message-in">
        <div className="max-w-[85%] rounded-2xl border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm leading-relaxed text-destructive">
          {message.content}
        </div>
      </div>
    )
  }

  const isUser = message.role === "user"

  return (
    <div className={cn("flex flex-col animate-message-in", isUser ? "items-end" : "items-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-2 text-sm leading-relaxed",
          isUser
            ? "bg-primary text-primary-foreground shadow-glow-sm whitespace-pre-wrap"
            : "border border-border/60 bg-card text-card-foreground"
        )}
      >
        {isUser ? message.content : <MarkdownContent content={message.content} />}
      </div>
      {!isUser && message.sources && message.sources.length > 0 && (
        <div className="mt-1.5 flex max-w-[85%] flex-wrap gap-1.5">
          {message.sources.map((s) => (
            <span
              key={`${s.document}-${s.section}`}
              className="rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 font-mono text-[10px] text-muted-foreground"
            >
              {s.document} <span className="text-primary">§{s.section}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="space-y-2 [&>*:last-child]:mb-0">
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="leading-relaxed">{children}</p>,
          strong: ({ children }) => (
            <strong className="font-semibold text-primary">{children}</strong>
          ),
          ul: ({ children }) => <ul className="ml-4 list-disc space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="ml-4 list-decimal space-y-1">{children}</ol>,
          li: ({ children }) => <li className="pl-1">{children}</li>,
          a: ({ children, href }) => (
            <a href={href} className="text-primary underline underline-offset-2">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-start animate-message-in">
      <div className="flex items-center gap-1 rounded-2xl border border-border/60 bg-card px-4 py-3 shadow-glow-sm">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="size-1.5 animate-bounce rounded-full bg-primary"
            style={{ animationDelay: `${i * 120}ms` }}
          />
        ))}
      </div>
    </div>
  )
}
