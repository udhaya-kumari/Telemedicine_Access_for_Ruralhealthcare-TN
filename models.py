from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
   
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=True, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(20), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    doctor = db.relationship("Doctor", back_populates="user", uselist=False, cascade="all, delete-orphan")
    patient = db.relationship("Patient", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)
        self.password = None

    def check_password(self, raw_password):
        if self.password_hash and check_password_hash(self.password_hash, raw_password):
            return True
        return bool(self.password and self.password == raw_password)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    reg_no = db.Column(db.String(50), unique=True, nullable=True, index=True)
    qualification = db.Column(db.String(120), nullable=True)
    specialization = db.Column(db.String(120), nullable=True, index=True)
    hospital = db.Column(db.String(180), nullable=True)
    experience = db.Column(db.Integer, nullable=True)
    location = db.Column(db.String(160), nullable=True, index=True)
    is_available = db.Column(db.Boolean, default=True, nullable=False)

    # Added for the "Consult Doctor" search/booking feature.
    symptoms_treated = db.Column(db.Text, nullable=True)
    available_days = db.Column(db.String(160), nullable=True)
    available_slots = db.Column(db.String(255), nullable=True)
    consultation_fee = db.Column(db.Numeric(8, 2), nullable=True)
    photo_url = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="doctor")
    slots = db.relationship("DoctorSlot", back_populates="doctor", cascade="all, delete-orphan")
    appointments = db.relationship("Appointment", back_populates="doctor")

    def __repr__(self):
        return f"<Doctor Dr. {self.name}>"


class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(20), nullable=True, index=True)
    blood_group = db.Column(db.String(10), nullable=True)
    address = db.Column(db.Text, nullable=True)
    village = db.Column(db.String(120), nullable=True)
    district = db.Column(db.String(120), nullable=True, default="Tamil Nadu")
    location = db.Column(db.String(160), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="patient")
    appointments = db.relationship("Appointment", back_populates="patient")
    medical_records = db.relationship("MedicalRecord", back_populates="patient", cascade="all, delete-orphan")
    emergency_requests = db.relationship("EmergencyRequest", back_populates="patient", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Patient {self.name}>"



class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)
    slot_id = db.Column(db.Integer, db.ForeignKey("doctor_slots.id"), nullable=True, index=True)
    status = db.Column(db.String(30), default="PENDING", nullable=False, index=True)
    reason = db.Column(db.Text, nullable=True)
    jitsi_link = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")
    slot = db.relationship("DoctorSlot", back_populates="appointments")
    chat_messages = db.relationship("ChatMessage", back_populates="appointment", cascade="all, delete-orphan")
    medical_records = db.relationship("MedicalRecord", back_populates="appointment")

    def __repr__(self):
        return f"<Appointment {self.id} {self.status}>"





class DoctorSlot(db.Model):
    __tablename__ = "doctor_slots"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False, index=True)

    # The backend/frontend pair accepts both naming styles.
    date = db.Column(db.String(20), nullable=True, index=True)
    slot_date = db.Column(db.String(20), nullable=True, index=True)
    slot_time = db.Column(db.String(20), nullable=True)
    start_time = db.Column(db.String(20), nullable=True)
    end_time = db.Column(db.String(20), nullable=True)

    status = db.Column(db.String(20), default="AVAILABLE", nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    doctor = db.relationship("Doctor", back_populates="slots")
    appointments = db.relationship("Appointment", back_populates="slot")

    def __repr__(self):
        return f"<DoctorSlot doctor={self.doctor_id} status={self.status}>"



class MedicalRecord(db.Model):
    __tablename__ = "medical_records"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=True, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(500), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = db.relationship("Patient", back_populates="medical_records")
    appointment = db.relationship("Appointment", back_populates="medical_records")

    def __repr__(self):
        return f"<MedicalRecord {self.title}>"


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    sender_role = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=True)
    text = db.Column(db.Text, nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    file_url = db.Column(db.String(500), nullable=True)
    file_type = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    appointment = db.relationship("Appointment", back_populates="chat_messages")
    sender = db.relationship("User")

    def __repr__(self):
        return f"<ChatMessage appointment={self.appointment_id} sender={self.sender_id}>"


class EmergencyRequest(db.Model):
    __tablename__ = "emergency_requests"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    symptoms = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(180), nullable=True)
    contact_number = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(30), default="PENDING", nullable=False, index=True)
    assigned_doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = db.relationship("Patient", back_populates="emergency_requests")
    assigned_doctor = db.relationship("Doctor")

    def __repr__(self):
        return f"<EmergencyRequest {self.id} {self.status}>"