"use client"

import * as React from "react"
import { Send } from "lucide-react"

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
    <div className="mx-auto flex h-svh w-full max-w-2xl flex-col">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <div>
          <h1 className="text-sm font-semibold">Baobab Freight Assistant</h1>
          <p className="text-xs text-muted-foreground">
            Ask about customs, SLAs, claims, and compliance for Baobab Freight & Logistics.
          </p>
        </div>
        <ThemeToggle />
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4">
        <div className="flex flex-col gap-4">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {isSending && <TypingIndicator />}
        </div>
      </div>

      <div className="border-t border-border px-4 py-3">
        <div className="mb-2 text-xs text-muted-foreground">
          {limitReached
            ? "You've used all your questions for this session."
            : `${remaining} question${remaining === 1 ? "" : "s"} remaining`}
        </div>
        <div className="flex items-center gap-2">
          <Input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={limitReached ? "No questions remaining" : "Ask a question..."}
            disabled={isSending || limitReached}
            aria-label="Your question"
          />
          <Button onClick={handleSend} disabled={!canSend} size="icon" aria-label="Send">
            <Send className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "error") {
    return (
      <div className="flex flex-col items-start">
        <div className="max-w-[85%] rounded-2xl border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm leading-relaxed text-destructive">
          {message.content}
        </div>
      </div>
    )
  }

  const isUser = message.role === "user"

  return (
    <div className={cn("flex flex-col", isUser ? "items-end" : "items-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground"
        )}
      >
        {message.content}
      </div>
      {!isUser && message.sources && message.sources.length > 0 && (
        <div className="mt-1 max-w-[85%] text-xs text-muted-foreground">
          {message.sources.map((s, i) => (
            <span key={`${s.document}-${s.section}`}>
              {i > 0 && " · "}
              {s.document} §{s.section}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-start">
      <div className="flex items-center gap-1 rounded-2xl bg-muted px-4 py-3">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="size-1.5 animate-bounce rounded-full bg-muted-foreground"
            style={{ animationDelay: `${i * 120}ms` }}
          />
        ))}
      </div>
    </div>
  )
}
