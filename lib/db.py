import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/clinic_bot")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="patient")

class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    doctor_or_service = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    is_available = Column(Boolean, default=True)

    appointments = relationship("Appointment", back_populates="slot")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    slot_id = Column(Integer, ForeignKey("slots.id"))
    status = Column(String, default="pending")  # pending, booked, confirmed, cancelled, completed, no_show
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    slot = relationship("Slot", back_populates="appointments")

class WaitingList(Base):
    __tablename__ = "waiting_list"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    desired_date_range = Column(String)
    service = Column(String)
    status = Column(String, default="waiting")  # waiting, offered, expired
    created_at = Column(DateTime, default=datetime.utcnow)

class ConversationState(Base):
    __tablename__ = "conversation_state"

    phone_number = Column(String, primary_key=True, index=True)
    current_step = Column(String)
    context_json = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
