// ─────────────────────────────────────────────────────────────────────────────
// WhatsApp Cloud API helpers
// Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
// ─────────────────────────────────────────────────────────────────────────────

const BASE_URL = "https://graph.facebook.com/v20.0";

function headers() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${process.env.WHATSAPP_TOKEN}`,
  };
}

function phoneId() {
  const id = process.env.WHATSAPP_PHONE_NUMBER_ID;
  if (!id) throw new Error("WHATSAPP_PHONE_NUMBER_ID not set");
  return id;
}

// ── Send plain text ────────────────────────────────────────────────────────────

export async function sendText(to: string, body: string) {
  return _send(to, { type: "text", text: { body, preview_url: false } });
}

// ── Send interactive buttons (up to 3) ────────────────────────────────────────

export async function sendButtons(
  to: string,
  bodyText: string,
  buttons: { id: string; title: string }[]
) {
  return _send(to, {
    type: "interactive",
    interactive: {
      type: "button",
      body: { text: bodyText },
      action: {
        buttons: buttons.map((b) => ({
          type: "reply",
          reply: { id: b.id, title: b.title },
        })),
      },
    },
  });
}

// ── Send a list of available slots ────────────────────────────────────────────

export async function sendSlotList(
  to: string,
  slots: { id: number; doctor_or_service: string; start_time: string }[]
) {
  const rows = slots
    .map(
      (s, i) =>
        `${i + 1}. *${s.doctor_or_service}* — ${new Date(s.start_time).toLocaleString(
          "en-IN",
          { dateStyle: "medium", timeStyle: "short" }
        )}`
    )
    .join("\n");

  const prompt =
    slots.length > 0
      ? `Here are the available slots:\n\n${rows}\n\nReply with the number of your preferred slot.`
      : "Sorry, no slots are currently available for your request. Would you like to join the waiting list?";

  return sendText(to, prompt);
}

// ── Send appointment confirmation ─────────────────────────────────────────────

export async function sendConfirmation(
  to: string,
  name: string,
  service: string,
  startTime: string
) {
  const time = new Date(startTime).toLocaleString("en-IN", {
    dateStyle: "full",
    timeStyle: "short",
  });
  const msg =
    `✅ *Appointment Confirmed!*\n\n` +
    `Hi ${name}, your appointment has been booked.\n\n` +
    `📋 *Service:* ${service}\n` +
    `🕐 *Date & Time:* ${time}\n\n` +
    `We'll send you a reminder before your appointment. Reply *CANCEL* anytime to cancel.`;
  return sendText(to, msg);
}

// ── Send reminder with confirm / cancel buttons ───────────────────────────────

export async function sendReminder(
  to: string,
  name: string,
  service: string,
  startTime: string,
  appointmentId: number
) {
  const time = new Date(startTime).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
  return sendButtons(
    to,
    `⏰ *Reminder*\n\nHi ${name}, your appointment for *${service}* is on *${time}*.\n\nPlease confirm your attendance:`,
    [
      { id: `CONFIRM_${appointmentId}`, title: "✅ Confirm" },
      { id: `CANCEL_${appointmentId}`, title: "❌ Cancel" },
    ]
  );
}

// ── Notify waiting-list patient ───────────────────────────────────────────────

export async function sendWaitingListOffer(
  to: string,
  name: string,
  service: string,
  startTime: string,
  slotId: number
) {
  const time = new Date(startTime).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
  return sendButtons(
    to,
    `🎉 Good news ${name}! A slot has opened up:\n\n*${service}* on *${time}*\n\nWould you like to book it?`,
    [
      { id: `WAITLIST_ACCEPT_${slotId}`, title: "✅ Book it!" },
      { id: `WAITLIST_DECLINE_${slotId}`, title: "❌ No thanks" },
    ]
  );
}

// ── Internal fetch wrapper ────────────────────────────────────────────────────

async function _send(to: string, messagePayload: Record<string, unknown>) {
  const url = `${BASE_URL}/${phoneId()}/messages`;
  const res = await fetch(url, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      messaging_product: "whatsapp",
      recipient_type: "individual",
      to,
      ...messagePayload,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    console.error("[WhatsApp] Send failed:", err);
    throw new Error(`WhatsApp API error: ${res.status}`);
  }

  return res.json();
}

// ── Parse inbound webhook body ────────────────────────────────────────────────

export type InboundMessage =
  | { type: "text"; from: string; text: string; messageId: string }
  | { type: "button_reply"; from: string; buttonId: string; messageId: string }
  | { type: "unsupported"; from: string };

export function parseInboundMessage(body: unknown): InboundMessage | null {
  try {
    const entry = (body as any).entry?.[0];
    const change = entry?.changes?.[0];
    const msg = change?.value?.messages?.[0];
    if (!msg) return null;

    const from: string = msg.from;
    const messageId: string = msg.id;

    if (msg.type === "text") {
      return { type: "text", from, text: msg.text.body, messageId };
    }
    if (msg.type === "interactive" && msg.interactive?.type === "button_reply") {
      return {
        type: "button_reply",
        from,
        buttonId: msg.interactive.button_reply.id,
        messageId,
      };
    }
    return { type: "unsupported", from };
  } catch {
    return null;
  }
}
