"use client"

import * as React from "react"
import { Send } from "lucide-react"
import ReactMarkdown from "react-markdown"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ThemeToggle } from "@/components/chat/theme-toggle"
import { Brand, Sidebar, TOPICS } from "@/components/chat/sidebar"
import { ServerStatusBanner, SlowRequestHint } from "@/components/server-status"
import { useBackendStatus } from "@/hooks/use-backend-status"
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
  const inputRef = React.useRef<HTMLInputElement>(null)
  const backendStatus = useBackendStatus()

  React.useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [messages, isSending])

  const limitReached = remaining <= 0
  const canSend = input.trim().length > 0 && !isSending && !limitReached

  async function sendQuestion(question: string) {
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

  function handleSend() {
    if (!canSend) return
    sendQuestion(input.trim())
  }

  function handlePickTopic(question: string) {
    if (isSending || limitReached) return
    sendQuestion(question)
    inputRef.current?.focus()
  }

  // Mobile has no sidebar, so the empty thread offers the same topics. These only
  // fill the input rather than sending, so a visitor can read and edit first - and
  // isn't spending one of their daily questions on a tap while the server wakes.
  function handleFillTopic(question: string) {
    setInput(question)
    inputRef.current?.focus()
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-dvh flex-col bg-background">
      {/* Flat header, capped to the same centred column as the panels below */}
      <header className="shrink-0 pt-4">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
          <Brand />
          <div className="flex items-center gap-2">
            <RemainingIndicator remaining={remaining} limitReached={limitReached} />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 gap-4 px-4 pt-4 pb-[calc(env(safe-area-inset-bottom)+1rem)] sm:px-6 sm:pb-6">
        <Sidebar onPickTopic={handlePickTopic} />

        <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-3xl border border-border">
          <div ref={scrollRef} className="flex-1 overflow-y-auto">
            <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-6 lg:px-8">
              <ServerStatusBanner status={backendStatus} />
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              {messages.length === INITIAL_MESSAGES.length && !isSending && (
                <MobileTopics onPick={handleFillTopic} />
              )}
              {isSending && (
                <div className="flex flex-col gap-2">
                  <TypingIndicator />
                  <SlowRequestHint />
                </div>
              )}
            </div>
          </div>

          <div className="px-3 pb-3 lg:px-6 lg:pb-5">
            <div className="mx-auto flex max-w-3xl items-center gap-2 rounded-full bg-muted p-1.5 pl-5">
              <Input
                ref={inputRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={limitReached ? "No questions remaining" : "Ask a question..."}
                disabled={isSending || limitReached}
                aria-label="Your question"
                className="border-none bg-transparent px-0 shadow-none focus-visible:ring-0"
              />
              <Button onClick={handleSend} disabled={!canSend} size="icon" aria-label="Send" className="shrink-0">
                <Send className="size-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function RemainingIndicator({ remaining, limitReached }: { remaining: number; limitReached: boolean }) {
  return (
    <div
      className={cn(
        "flex items-center rounded-full px-3 py-1.5 font-mono text-[11px] font-medium tracking-wide uppercase",
        limitReached ? "bg-destructive/15 text-destructive" : "bg-sand text-on-accent"
      )}
    >
      {limitReached
        ? "Daily limit reached"
        : `${remaining} question${remaining === 1 ? "" : "s"} remaining`}
    </div>
  )
}

function MobileTopics({ onPick }: { onPick: (question: string) => void }) {
  return (
    <div className="flex flex-wrap gap-1.5 lg:hidden">
      {TOPICS.map((topic) => (
        <button
          key={topic.label}
          type="button"
          onClick={() => onPick(topic.question)}
          className="rounded-full bg-sky px-3.5 py-1.5 text-xs font-semibold text-on-accent transition-colors hover:bg-primary hover:text-primary-foreground"
        >
          {topic.label}
        </button>
      ))}
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === "error") {
    return (
      <div className="flex flex-col items-start animate-message-in">
        <div className="max-w-[85%] rounded-3xl bg-destructive/10 px-5 py-3 text-sm leading-relaxed text-destructive">
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
          "max-w-[85%] rounded-3xl px-5 py-3 text-sm leading-relaxed",
          isUser
            ? "rounded-br-lg bg-primary text-primary-foreground whitespace-pre-wrap"
            : "rounded-bl-lg bg-card text-card-foreground"
        )}
      >
        {isUser ? message.content : <MarkdownContent content={message.content} />}
      </div>
      {!isUser && message.sources && message.sources.length > 0 && (
        <div className="mt-1.5 flex max-w-[85%] flex-wrap gap-1.5">
          {message.sources.map((s) => (
            <span
              key={`${s.document}-${s.section}`}
              className="rounded-full bg-muted px-2.5 py-1 font-mono text-[10px] text-muted-foreground"
            >
              {s.document} <span className="font-semibold text-foreground">§{s.section}</span>
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
            <strong className="font-semibold text-foreground">{children}</strong>
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
      <div className="flex items-center gap-1 rounded-3xl rounded-bl-lg bg-card px-5 py-4">
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
