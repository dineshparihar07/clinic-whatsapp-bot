import { GoogleGenerativeAI } from "@google/generative-ai";

let client: GoogleGenerativeAI | null = null;

function getClient() {
  if (!client) {
    const key = process.env.GEMINI_API_KEY;
    if (!key) throw new Error("GEMINI_API_KEY not set");
    client = new GoogleGenerativeAI(key);
  }
  return client;
}

// ── Intent + entity extraction ────────────────────────────────────────────────

export type Intent =
  | "book_appointment"
  | "cancel_appointment"
  | "reschedule_appointment"
  | "check_status"
  | "join_waitlist"
  | "faq"
  | "greeting"
  | "unknown";

export interface ParsedMessage {
  intent: Intent;
  service?: string;          // e.g. "General Checkup", "Dental"
  doctor?: string;           // if patient specifies a doctor name
  date?: string;             // ISO date string YYYY-MM-DD
  time?: string;             // e.g. "morning", "10:30", "afternoon"
  slotNumber?: number;       // when patient replies with slot index
  replyText: string;         // natural language reply to send back to patient
  confidence: "high" | "low";
}

const SYSTEM_PROMPT = `
You are a friendly clinic receptionist bot for WhatsApp.
The clinic offers these services: General Checkup, Dental, Dermatology, Pediatrics, Cardiology.
Clinic hours: Monday–Saturday, 9 AM to 6 PM.

Your job is to understand what the patient wants and extract structured data.
Always respond in valid JSON only — no markdown, no extra text.

Output this exact shape:
{
  "intent": one of [book_appointment, cancel_appointment, reschedule_appointment, check_status, join_waitlist, faq, greeting, unknown],
  "service": string or null,
  "doctor": string or null,
  "date": "YYYY-MM-DD" or null,
  "time": string or null,
  "slotNumber": integer or null,
  "replyText": "friendly reply to send to the patient",
  "confidence": "high" or "low"
}

Rules:
- If the patient says a number like "1" or "option 2", set slotNumber to that integer.
- If date is relative ("tomorrow", "next Monday"), convert to YYYY-MM-DD relative to today: ${new Date().toISOString().split("T")[0]}.
- If you're unsure about the intent, set intent to "unknown" and confidence to "low", and ask a clarifying question in replyText.
- Keep replyText warm, concise, and in the same language the patient used.
`;

export async function parsePatientMessage(
  message: string,
  conversationHistory: { role: string; text: string }[] = []
): Promise<ParsedMessage> {
  const genAI = getClient();
  const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

  // Build conversation context string
  const historyText =
    conversationHistory.length > 0
      ? conversationHistory
          .slice(-6) // last 3 exchanges
          .map((h) => `${h.role}: ${h.text}`)
          .join("\n") + "\n"
      : "";

  const prompt = `${SYSTEM_PROMPT}\n\nConversation so far:\n${historyText}Patient: ${message}`;

  const result = await model.generateContent(prompt);
  const raw = result.response.text().trim();

  try {
    // Strip possible code fences
    const cleaned = raw.replace(/```json|```/g, "").trim();
    return JSON.parse(cleaned) as ParsedMessage;
  } catch {
    console.error("[Gemini] Failed to parse response:", raw);
    return {
      intent: "unknown",
      replyText:
        "I'm sorry, I didn't quite understand that. Could you tell me if you'd like to book, cancel, or check an appointment?",
      confidence: "low",
    };
  }
}

// ── Simple FAQ answer ─────────────────────────────────────────────────────────

export async function answerFaq(question: string): Promise<string> {
  const genAI = getClient();
  const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

  const prompt = `
You are a clinic receptionist answering a patient's question over WhatsApp.
Clinic: City Care Clinic
Services: General Checkup, Dental, Dermatology, Pediatrics, Cardiology
Hours: Mon–Sat 9 AM – 6 PM
Location: Please call reception for directions.
Answer briefly and warmly. If you don't know, say to call the clinic directly.

Question: ${question}
`;

  const result = await model.generateContent(prompt);
  return result.response.text().trim();
}
