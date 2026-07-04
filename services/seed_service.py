"""Seeds sample data (doctors, patients, appointments) when the tables are empty.

This only ever INSERTs when the relevant tables have zero rows, so it never
touches or duplicates real data created by users.
"""
from datetime import date, timedelta

from extensions import db
from models import Appointment, Doctor, DoctorSlot, Patient, User


SAMPLE_DOCTORS = [
    {
        "name": "Dr Kumar",
        "email": "dr.kumar@telemed.test",
        "reg_no": "TN-MED-10001",
        "specialization": "Cardiologist",
        "qualification": "MBBS, MD (Cardiology)",
        "experience": 14,
        "hospital": "Coimbatore Heart Institute",
        "location": "Coimbatore",
        "consultation_fee": 500,
        "available_days": "Mon, Wed, Fri",
        "symptoms_treated": "Chest Pain, Heart Disease, High BP",
        "bio": "Specialist in interventional cardiology and preventive heart care.",
    },
    {
        "name": "Dr Priya",
        "email": "dr.priya@telemed.test",
        "reg_no": "TN-MED-10002",
        "specialization": "Dermatologist",
        "qualification": "MBBS, MD (Dermatology)",
        "experience": 9,
        "hospital": "Sunrise Skin Clinic",
        "location": "Chennai",
        "consultation_fee": 400,
        "available_days": "Tue, Thu, Sat",
        "symptoms_treated": "Acne, Skin Allergy, Rash",
        "bio": "Focused on skin allergies, acne management, and cosmetic dermatology.",
    },
    {
        "name": "Dr Arun",
        "email": "dr.arun@telemed.test",
        "reg_no": "TN-MED-10003",
        "specialization": "Orthopedic",
        "qualification": "MBBS, MS (Orthopedics)",
        "experience": 11,
        "hospital": "Tamil Nadu Ortho Center",
        "location": "Madurai",
        "consultation_fee": 450,
        "available_days": "Mon, Tue, Thu",
        "symptoms_treated": "Knee Pain, Fracture, Back Pain",
        "bio": "Experienced in joint care, sports injuries, and fracture management.",
    },
    {
        "name": "Dr Meena",
        "email": "dr.meena@telemed.test",
        "reg_no": "TN-MED-10004",
        "specialization": "General Physician",
        "qualification": "MBBS, MD (General Medicine)",
        "experience": 7,
        "hospital": "Village Health Clinic",
        "location": "Salem",
        "consultation_fee": 300,
        "available_days": "Mon - Sat",
        "symptoms_treated": "Fever, Cold, Diabetes",
        "bio": "General physician caring for everyday illnesses and chronic disease follow-ups.",
    },
    {
        "name": "Dr Sanjay",
        "email": "dr.sanjay@telemed.test",
        "reg_no": "TN-MED-10005",
        "specialization": "Neurologist",
        "qualification": "MBBS, DM (Neurology)",
        "experience": 16,
        "hospital": "Neuro Care Hospital",
        "location": "Coimbatore",
        "consultation_fee": 600,
        "available_days": "Wed, Fri, Sat",
        "symptoms_treated": "Migraine, Headache, Stroke",
        "bio": "Treats migraines, headaches, and neurological emergencies.",
    },
]

SAMPLE_TIME_SLOTS = ["09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "02:00 PM", "02:30 PM", "03:00 PM"]

SAMPLE_PATIENTS = [
    {"name": "Ravi Shankar", "email": "ravi.patient@telemed.test", "age": 34, "gender": "Male", "village": "Perur"},
    {"name": "Lakshmi Narayanan", "email": "lakshmi.patient@telemed.test", "age": 28, "gender": "Female", "village": "Annur"},
    {"name": "Suresh Babu", "email": "suresh.patient@telemed.test", "age": 45, "gender": "Male", "village": "Karamadai"},
    {"name": "Divya Bharathi", "email": "divya.patient@telemed.test", "age": 31, "gender": "Female", "village": "Mettupalayam"},
]

APPOINTMENT_STATUSES = ["PENDING", "PENDING", "ACCEPTED", "ACCEPTED", "COMPLETED", "COMPLETED", "REJECTED", "PENDING", "ACCEPTED", "COMPLETED"]


def _end_time(start_time):
    # Naive 30-minute slot end-time calculator for the "HH:MM AM/PM" format used above.
    from datetime import datetime as _dt

    parsed = _dt.strptime(start_time, "%I:%M %p")
    ended = parsed + timedelta(minutes=30)
    return ended.strftime("%I:%M %p")


def seed_sample_data():
    """Insert sample doctors/patients/appointments.

    Doctors and patients are seeded independently of each other, so a real
    patient signing up before doctors exist doesn't permanently block the
    sample doctors from ever being created (and vice versa). Appointments
    are only auto-generated the first time both sample doctors and sample
    patients are created together in this same call.
    """
    default_password = "Telemed@123"

    doctors = []
    doctor_slots = {}
    doctors_created = False
    if Doctor.query.count() == 0:
        doctors_created = True
        for entry in SAMPLE_DOCTORS:
            user = User(name=entry["name"], email=entry["email"], role="Doctor")
            user.set_password(default_password)
            db.session.add(user)
            db.session.flush()

            doctor = Doctor(
                user_id=user.id,
                name=entry["name"],
                reg_no=entry.get("reg_no"),
                qualification=entry["qualification"],
                specialization=entry["specialization"],
                hospital=entry["hospital"],
                experience=entry["experience"],
                location=entry["location"],
                is_available=True,
                symptoms_treated=entry["symptoms_treated"],
                available_days=entry["available_days"],
                available_slots=", ".join(SAMPLE_TIME_SLOTS),
                consultation_fee=entry["consultation_fee"],
                bio=entry["bio"],
            )
            db.session.add(doctor)
            db.session.flush()
            doctors.append(doctor)

        # Create bookable slots for each doctor across the next 5 days.
        today = date.today()
        doctor_slots = {doctor.id: [] for doctor in doctors}
        for doctor in doctors:
            for day_offset in range(5):
                slot_date = (today + timedelta(days=day_offset)).isoformat()
                for start_time in SAMPLE_TIME_SLOTS:
                    slot = DoctorSlot(
                        doctor_id=doctor.id,
                        date=slot_date,
                        slot_date=slot_date,
                        start_time=start_time,
                        slot_time=start_time,
                        end_time=_end_time(start_time),
                        status="AVAILABLE",
                    )
                    db.session.add(slot)
                    db.session.flush()
                    doctor_slots[doctor.id].append(slot)

    patients = []
    patients_created = False
    if Patient.query.count() == 0:
        patients_created = True
        for entry in SAMPLE_PATIENTS:
            user = User(name=entry["name"], email=entry["email"], role="Patient")
            user.set_password(default_password)
            db.session.add(user)
            db.session.flush()

            patient = Patient(
                user_id=user.id,
                name=entry["name"],
                age=entry["age"],
                gender=entry["gender"],
                village=entry["village"],
                district="Tamil Nadu",
            )
            db.session.add(patient)
            db.session.flush()
            patients.append(patient)

    # Only auto-generate sample appointments the first time both the sample
    # doctors and sample patients are created together, and only if there
    # are no appointments yet (never touches real bookings).
    if doctors_created and patients_created and Appointment.query.count() == 0:
        for index, status in enumerate(APPOINTMENT_STATUSES):
            doctor = doctors[index % len(doctors)]
            patient = patients[index % len(patients)]
            slot = doctor_slots[doctor.id][index % len(doctor_slots[doctor.id])]

            appointment = Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                slot_id=slot.id,
                status=status,
                reason="Sample consultation request.",
            )
            if status != "REJECTED":
                slot.status = "BOOKED"
            db.session.add(appointment)

    db.session.commit()
