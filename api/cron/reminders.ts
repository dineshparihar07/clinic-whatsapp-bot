import type { NextApiRequest, NextApiResponse } from "next";
import { getAppointmentsDueForReminder } from "@/lib/db";
import { sendReminder } from "@/lib/whatsapp";
import { getDb } from "@/lib/db";

// Vercel Cron hits this endpoint every 30 minutes (see vercel.json)
// Protect with a secret header so it can't be triggered arbitrarily

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "GET") return res.status(405).end();

  // Verify cron secret
  const secret = req.headers["x-cron-secret"];
  if (secret !== process.env.CRON_SECRET) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  try {
    // Find appointments starting within the next 24 hours (1440 min)
    const appointments = await getAppointmentsDueForReminder(1440);
    console.log(`[Cron] Found ${appointments.length} appointments needing reminders`);

    const db = getDb();
    let sent = 0;

    for (const appt of appointments) {
      try {
        await sendReminder(
          appt.phone_number,
          appt.name ?? "there",
          appt.doctor_or_service,
          appt.start_time,
          appt.id
        );

        // Mark reminder sent
        await db.query(
          `UPDATE appointments SET reminder_sent = TRUE WHERE id = $1`,
          [appt.id]
        );

        sent++;
        console.log(`[Cron] Reminder sent → appt #${appt.id} (${appt.phone_number})`);
      } catch (err) {
        console.error(`[Cron] Failed to send reminder for appt #${appt.id}:`, err);
      }
    }

    return res.status(200).json({ processed: appointments.length, sent });
  } catch (err) {
    console.error("[Cron] Reminders error:", err);
    return res.status(500).json({ error: "Internal server error" });
  }
}
