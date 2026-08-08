import type { NextApiRequest, NextApiResponse } from "next";
import {
  parseInboundMessage,
  sendText,
  sendSlotList,
  sendConfirmation,
  sendWaitingListOffer,
} from "@/lib/whatsapp";
import { parsePatientMessage } from "@/lib/gemini";
import {
  upsertPatient,
  getAvailableSlots,
  bookAppointment,
  updateAppointmentStatus,
  getConversationState,
  setConversationState,
  clearConversationState,
  addToWaitingList,
  getWaitingListForSlot,
} from "@/lib/db";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // ── Webhook verification (GET) ─────────────────────────────────────────────
  if (req.method === "GET") {
    const mode = req.query["hub.mode"];
    const token = req.query["hub.verify_token"];
    const challenge = req.query["hub.challenge"];

    if (mode === "subscribe" && token === process.env.WHATSAPP_VERIFY_TOKEN) {
      console.log("[Webhook] Verified ✓");
      return res.status(200).send(challenge);
    }
    return res.status(403).json({ error: "Forbidden" });
  }

  // ── Inbound message (POST) ─────────────────────────────────────────────────
  if (req.method === "POST") {
    // Always reply 200 immediately so Meta doesn't retry
    res.status(200).json({ status: "ok" });

    try {
      const msg = parseInboundMessage(req.body);
      if (!msg || msg.type === "unsupported") return;

      const phone = msg.from;

      // ── Handle button replies (confirm / cancel / waiting-list) ────────────
      if (msg.type === "button_reply") {
        await handleButtonReply(phone, msg.buttonId);
        return;
      }

      // ── Handle free-text messages ──────────────────────────────────────────
      if (msg.type === "text") {
        await handleTextMessage(phone, msg.text);
      }
    } catch (err) {
      console.error("[Webhook] Error:", err);
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Free-text message handler
// ─────────────────────────────────────────────────────────────────────────────

async function handleTextMessage(phone: string, text: string) {
  const state = await getConversationState(phone);
  const context = state?.context ?? {};
  const history = context.history ?? [];

  // Parse intent via Gemini
  const parsed = await parsePatientMessage(text, history);

  // Append to history
  history.push({ role: "patient", text });
  history.push({ role: "bot", text: parsed.replyText });
  if (history.length > 12) history.splice(0, 2); // trim

  switch (parsed.intent) {
    case "greeting":
      await sendText(phone, parsed.replyText);
      await setConversationState(phone, "idle", { history });
      break;

    case "book_appointment": {
      const patient = await upsertPatient(phone);
      const slots = await getAvailableSlots(parsed.service ?? undefined, parsed.date ?? undefined);

      if (slots.length === 0) {
        await sendText(
          phone,
          `Sorry, no slots are available right now for ${parsed.service ?? "your request"}. Would you like to join the waiting list? Reply *YES* to be notified when a slot opens.`
        );
        await setConversationState(phone, "ask_waitlist", {
          history,
          service: parsed.service,
          date: parsed.date,
          patientId: patient.id,
        });
        break;
      }

      await sendSlotList(phone, slots);
      await setConversationState(phone, "await_slot_choice", {
        history,
        slots: slots.map((s: any) => ({ id: s.id, start_time: s.start_time, service: s.doctor_or_service })),
        patientId: patient.id,
      });
      break;
    }

    case "cancel_appointment": {
      // TODO Phase 6: look up active appointment for this patient and cancel
      await sendText(phone, parsed.replyText);
      break;
    }

    case "join_waitlist":
    case "unknown": {
      // Check if we're mid-flow awaiting a slot number
      if (state?.current_step === "await_slot_choice") {
        const slotNumber = parsed.slotNumber ?? parseInt(text.trim(), 10);
        if (!isNaN(slotNumber) && slotNumber > 0) {
          const slots = context.slots ?? [];
          const chosen = slots[slotNumber - 1];
          if (chosen) {
            await completeBooking(phone, context.patientId, chosen, history);
            return;
          }
        }
        await sendText(phone, "Please reply with the slot number (e.g. 1, 2, 3).");
        return;
      }

      if (state?.current_step === "ask_waitlist" && /yes/i.test(text)) {
        await addToWaitingList(
          context.patientId,
          context.service ?? "General",
          context.date ?? new Date().toISOString().split("T")[0]
        );
        await sendText(phone, "✅ You've been added to the waiting list! We'll notify you as soon as a slot opens.");
        await clearConversationState(phone);
        return;
      }

      await sendText(phone, parsed.replyText);
      await setConversationState(phone, "idle", { history });
      break;
    }

    default:
      await sendText(phone, parsed.replyText);
      await setConversationState(phone, "idle", { history });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Button reply handler
// ─────────────────────────────────────────────────────────────────────────────

async function handleButtonReply(phone: string, buttonId: string) {
  if (buttonId.startsWith("CONFIRM_")) {
    const appointmentId = parseInt(buttonId.replace("CONFIRM_", ""), 10);
    await updateAppointmentStatus(appointmentId, "confirmed");
    await sendText(phone, "✅ Great! Your appointment is confirmed. See you soon!");
    return;
  }

  if (buttonId.startsWith("CANCEL_")) {
    const appointmentId = parseInt(buttonId.replace("CANCEL_", ""), 10);
    const appt = await updateAppointmentStatus(appointmentId, "cancelled");
    await sendText(phone, "Your appointment has been cancelled. We hope to see you another time!");

    // Offer freed slot to waiting list
    if (appt?.slot_id) {
      const waiters = await getWaitingListForSlot(appt.slot_id);
      for (const w of waiters) {
        await sendWaitingListOffer(
          w.phone_number,
          w.name ?? "there",
          w.doctor_or_service,
          w.start_time,
          appt.slot_id
        );
      }
    }
    return;
  }

  if (buttonId.startsWith("WAITLIST_ACCEPT_")) {
    const slotId = parseInt(buttonId.replace("WAITLIST_ACCEPT_", ""), 10);
    const patient = await upsertPatient(phone);
    try {
      const appt = await bookAppointment(patient.id, slotId);
      await sendText(phone, `✅ Booked! You're all set. Appointment ID: #${appt.id}`);
    } catch {
      await sendText(phone, "Sorry, that slot was just taken. We'll notify you if another opens up!");
    }
    return;
  }

  if (buttonId.startsWith("WAITLIST_DECLINE_")) {
    await sendText(phone, "No problem! We'll let you know if other slots become available.");
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Complete a booking after patient picks a slot
// ─────────────────────────────────────────────────────────────────────────────

async function completeBooking(
  phone: string,
  patientId: number,
  slot: { id: number; start_time: string; service: string },
  history: { role: string; text: string }[]
) {
  try {
    const appt = await bookAppointment(patientId, slot.id);
    const patient = await upsertPatient(phone);
    await sendConfirmation(phone, patient.name ?? "there", slot.service, slot.start_time);
    await setConversationState(phone, "booked", {
      history,
      appointmentId: appt.id,
    });
  } catch (err: any) {
    if (err.message === "SLOT_TAKEN") {
      await sendText(phone, "Sorry, that slot was just taken by someone else. Let me fetch updated slots...");
      const freshSlots = await getAvailableSlots();
      await sendSlotList(phone, freshSlots);
    } else {
      throw err;
    }
  }
}
