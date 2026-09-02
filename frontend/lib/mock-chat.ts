import type { ChatMessage, Source } from "@/lib/chat-types"

export const RATE_LIMIT_PER_IP = 10

export const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: "seed-1",
    role: "assistant",
    content:
      "Hi, I'm the Baobab Freight Assistant. Ask me about customs, delivery SLAs, dangerous goods, claims, or any of our other policies.",
  },
]

type MockAnswer = {
  matches: (question: string) => boolean
  content: string
  sources: Source[]
}

const MOCK_ANSWERS: MockAnswer[] = [
  {
    matches: (q) => /vat|customs|duty/i.test(q),
    content:
      "Import VAT is levied at the standard rate of 15% on the customs value of goods entering South Africa (See the Customs and VAT Compliance Guide, Section 1).",
    sources: [{ document: "Customs and VAT Compliance Guide", section: "1" }],
  },
  {
    matches: (q) => /damag|claim/i.test(q),
    content:
      "Damage must be reported within 48 hours of delivery for domestic shipments, or 5 business days for cross-border SADC shipments (See the Damaged Goods Claims Process, Section 1).",
    sources: [{ document: "Damaged Goods Claims Process", section: "1" }],
  },
  {
    matches: (q) => /zambia|zimbabwe|botswana|mozambique|border/i.test(q),
    content:
      "Cross-border shipments require a commercial invoice, packing list, road manifest, SAD 500 customs declaration, and a Certificate of Origin where a SADC preference is claimed (See the Cross-Border Documentation Checklist — Overview, Section 1).",
    sources: [{ document: "Cross-Border Documentation Checklist — Overview", section: "1" }],
  },
  {
    matches: (q) => /lithium|batter|dangerous/i.test(q),
    content:
      "Lithium batteries are regulated under Class 9 due to fire risk from thermal runaway. Small consumer-type batteries within exempt limits may move under a simplified declaration; larger or damaged batteries require full Class 9 declaration and pre-approval (See the Dangerous Goods — Class 9: Miscellaneous Dangerous Goods, Section 1).",
    sources: [{ document: "Dangerous Goods — Class 9: Miscellaneous Dangerous Goods", section: "1" }],
  },
]

const FALLBACK_ANSWER: MockAnswer = {
  matches: () => true,
  content:
    "This is a mock response — the chat UI isn't wired to the real backend yet. Try asking about VAT, damaged goods claims, cross-border documents, or dangerous goods to see a canned example answer with citations.",
  sources: [],
}

export function getMockAnswer(question: string): { content: string; sources: Source[] } {
  const match = MOCK_ANSWERS.find((entry) => entry.matches(question)) ?? FALLBACK_ANSWER
  return { content: match.content, sources: match.sources }
}
