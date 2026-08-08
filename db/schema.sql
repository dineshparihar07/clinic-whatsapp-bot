-- ============================================================
-- Clinic WhatsApp Bot — Database Schema
-- Run once against your Postgres database to initialise tables
-- ============================================================

-- Patients registered via WhatsApp
CREATE TABLE IF NOT EXISTS patients (
  id            SERIAL PRIMARY KEY,
  phone_number  VARCHAR(20) UNIQUE NOT NULL,  -- E.164 format e.g. +919876543210
  name          VARCHAR(120),
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Available appointment slots (pre-populated by clinic admin)
CREATE TABLE IF NOT EXISTS slots (
  id               SERIAL PRIMARY KEY,
  doctor_or_service VARCHAR(120) NOT NULL,
  start_time       TIMESTAMPTZ NOT NULL,
  end_time         TIMESTAMPTZ NOT NULL,
  is_available     BOOLEAN DEFAULT TRUE,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Appointments booked by patients
CREATE TABLE IF NOT EXISTS appointments (
  id              SERIAL PRIMARY KEY,
  patient_id      INTEGER REFERENCES patients(id) ON DELETE CASCADE,
  slot_id         INTEGER REFERENCES slots(id) ON DELETE SET NULL,
  status          VARCHAR(20) NOT NULL DEFAULT 'booked'
                  CHECK (status IN ('pending','booked','confirmed','cancelled','completed','no_show')),
  reminder_sent   BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Patients waiting for a slot that is currently full
CREATE TABLE IF NOT EXISTS waiting_list (
  id                SERIAL PRIMARY KEY,
  patient_id        INTEGER REFERENCES patients(id) ON DELETE CASCADE,
  doctor_or_service VARCHAR(120),
  desired_date      DATE,
  status            VARCHAR(20) NOT NULL DEFAULT 'waiting'
                    CHECK (status IN ('waiting','offered','accepted','expired')),
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Conversation state — persists multi-turn WhatsApp flow between webhook calls
CREATE TABLE IF NOT EXISTS conversation_state (
  phone_number  VARCHAR(20) PRIMARY KEY,
  current_step  VARCHAR(60),          -- e.g. 'ask_service', 'ask_date', 'confirm_booking'
  context       JSONB DEFAULT '{}',   -- stores partial booking data between messages
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ── Useful indexes ────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_slots_start_time      ON slots(start_time);
CREATE INDEX IF NOT EXISTS idx_slots_available       ON slots(is_available);
CREATE INDEX IF NOT EXISTS idx_appointments_status   ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_appointments_slot     ON appointments(slot_id);
