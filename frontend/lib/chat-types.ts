export type Source = {
  document: string
  section: string
}

export type ChatMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  sources?: Source[]
}
