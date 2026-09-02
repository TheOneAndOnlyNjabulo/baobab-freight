import type { Source } from "@/lib/chat-types"

const API_URL = process.env.NEXT_PUBLIC_API_URL

export type ChatApiResponse = {
  answer: string
  sources: Source[]
  remaining_questions: number
}

export class ChatApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function sendChatMessage(question: string): Promise<ChatApiResponse> {
  if (!API_URL) {
    throw new ChatApiError(0, "NEXT_PUBLIC_API_URL is not configured.")
  }

  let response: Response
  try {
    response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    })
  } catch {
    throw new ChatApiError(0, "Couldn't reach the assistant. Check your connection and try again.")
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    if (response.status === 429) {
      throw new ChatApiError(429, detail ?? "You've used all your questions for this session.")
    }
    throw new ChatApiError(response.status, detail ?? "Failed to generate an answer. Please try again.")
  }

  return response.json()
}
