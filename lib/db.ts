import { Pool } from "pg";

// Re-use the connection pool across serverless function invocations
let pool: Pool | null = null;

export function getDb(): Pool {
  if (!pool) {
    if (!process.env.DATABASE_URL) {
      throw new Error("DATABASE_URL environment variable is not set");
    }
    pool = new Pool({
      connectionString: process.env.DATABASE_URL,
      ssl: { rejectUnauthorized: false }, // required for Neon / Supabase
      max: 5,
    });
  }
  return pool;
}

// ── Patient helpers ────────────────────────────────────────────────────────────

export async function upsertPatient(phone: string, name?: string) {
  const db = getDb();
  const { rows } = await db.query(
    `INSERT INTO patients (phone_number, name)
     VALUES ($1, $2)
     ON CONFLICT (phone_number)
     DO UPDATE SET name = COALESCE(EXCLUDED.name, patients.name)
     RETURNING *`,
    [phone, name ?? null]
  );
  return rows[0];
}

// ── Slot helpers ───────────────────────────────────────────────────────────────

export async function getAvailableSlots(service?: string, date?: string) {
  const db = getDb();
  let query = `SELECT * FROM slots WHERE is_available = TRUE AND start_time > NOW()`;
  const params: (string | undefined)[] = [];

  if (service) {
    params.push(service);
    query += ` AND LOWER(doctor_or_service) ILIKE $${params.length}`;
  }
  if (date) {
    params.push(date);
    query += ` AND DATE(start_time) = $${params.length}`;
  }
  query += ` ORDER BY start_time LIMIT 10`;

  const { rows } = await db.query(query, params);
  return rows;
}

// ── Appointment helpers ────────────────────────────────────────────────────────

export async function bookAppointment(patientId: number, slotId: number) {
  const db = getDb();
  const client = await db.connect();
  try {
    await client.query("BEGIN");

    // Lock the slot row to prevent race conditions
    const { rows: lockRows } = await client.query(
      `SELECT id FROM slots WHERE id = $1 AND is_available = TRUE FOR UPDATE`,
      [slotId]
    );
    if (lockRows.length === 0) throw new Error("SLOT_TAKEN");

    await client.query(`UPDATE slots SET is_available = FALSE WHERE id = $1`, [slotId]);

    const { rows } = await client.query(
      `INSERT INTO appointments (patient_id, slot_id, status)
       VALUES ($1, $2, 'booked') RETURNING *`,
      [patientId, slotId]
    );

    await client.query("COMMIT");
    return rows[0];
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

export async function updateAppointmentStatus(
  appointmentId: number,
  status: string
) {
  const db = getDb();
  const { rows } = await db.query(
    `UPDATE appointments SET status = $1, updated_at = NOW()
     WHERE id = $2 RETURNING *`,
    [status, appointmentId]
  );
  return rows[0];
}

export async function getAppointmentsDueForReminder(windowMinutes = 1440) {
  const db = getDb();
  const { rows } = await db.query(
    `SELECT a.*, p.phone_number, p.name, s.start_time, s.doctor_or_service
     FROM appointments a
     JOIN patients p ON p.id = a.patient_id
     JOIN slots s ON s.id = a.slot_id
     WHERE a.status IN ('booked','confirmed')
       AND a.reminder_sent = FALSE
       AND s.start_time BETWEEN NOW() AND NOW() + ($1 || ' minutes')::INTERVAL`,
    [windowMinutes]
  );
  return rows;
}

// ── Conversation state ─────────────────────────────────────────────────────────

export async function getConversationState(phone: string) {
  const db = getDb();
  const { rows } = await db.query(
    `SELECT * FROM conversation_state WHERE phone_number = $1`,
    [phone]
  );
  return rows[0] ?? null;
}

export async function setConversationState(
  phone: string,
  step: string,
  context: Record<string, unknown>
) {
  const db = getDb();
  await db.query(
    `INSERT INTO conversation_state (phone_number, current_step, context, updated_at)
     VALUES ($1, $2, $3, NOW())
     ON CONFLICT (phone_number)
     DO UPDATE SET current_step = EXCLUDED.current_step,
                   context = EXCLUDED.context,
                   updated_at = NOW()`,
    [phone, step, JSON.stringify(context)]
  );
}

export async function clearConversationState(phone: string) {
  const db = getDb();
  await db.query(`DELETE FROM conversation_state WHERE phone_number = $1`, [phone]);
}

// ── Waiting list ───────────────────────────────────────────────────────────────

export async function addToWaitingList(
  patientId: number,
  service: string,
  desiredDate: string
) {
  const db = getDb();
  const { rows } = await db.query(
    `INSERT INTO waiting_list (patient_id, doctor_or_service, desired_date)
     VALUES ($1, $2, $3) RETURNING *`,
    [patientId, service, desiredDate]
  );
  return rows[0];
}

export async function getWaitingListForSlot(slotId: number) {
  const db = getDb();
  const { rows } = await db.query(
    `SELECT wl.*, p.phone_number, p.name
     FROM waiting_list wl
     JOIN patients p ON p.id = wl.patient_id
     JOIN slots s ON s.doctor_or_service = wl.doctor_or_service
                  AND DATE(s.start_time) = wl.desired_date
     WHERE s.id = $1 AND wl.status = 'waiting'
     ORDER BY wl.created_at LIMIT 5`,
    [slotId]
  );
  return rows;
}
