from flask import Blueprint, request
from sqlalchemy import or_

from models import Doctor, DoctorSlot
from services.session_service import json_response, login_required


search_bp = Blueprint("search", __name__)


SYMPTOM_SPECIALIZATION_MAP = {
    "skin": "Dermatology",
    "skin irritation": "Dermatology",
    "rash": "Dermatology",
    "fever": "General Medicine",
    "cold": "General Medicine",
    "cough": "Pulmonology",
    "chest pain": "Cardiology",
    "heart": "Cardiology",
    "pregnancy": "Gynecology",
    "child": "Pediatrics",
    "eye": "Ophthalmology",
    "tooth": "Dentistry",
    "bone": "Orthopedics",
}


def _serialize_doctor(doctor):
    return {
        "id": doctor.id,
        "name": getattr(doctor, "name", None),
        "qualification": getattr(doctor, "qualification", None),
        "specialization": getattr(doctor, "specialization", None),
        "specialty": getattr(doctor, "specialization", None),
        "hospital": getattr(doctor, "hospital", None),
        "experience": getattr(doctor, "experience", None),
        "location": getattr(doctor, "location", None),
        "available_slots": DoctorSlot.query.filter_by(doctor_id=doctor.id, status="AVAILABLE").count(),
    }


@search_bp.get("/search-doctor")
@login_required
def search_doctor():
    query = (request.args.get("q") or request.args.get("query") or request.args.get("search") or "").strip()
    specialization = request.args.get("specialization")
    symptoms = (request.args.get("symptoms") or query).lower()

    mapped_specialization = None
    for keyword, mapped in SYMPTOM_SPECIALIZATION_MAP.items():
        if keyword in symptoms:
            mapped_specialization = mapped
            break

    filters = []
    if query:
        filters.extend([
            Doctor.name.ilike(f"%{query}%"),
            Doctor.specialization.ilike(f"%{query}%"),
        ])
    if specialization:
        filters.append(Doctor.specialization.ilike(f"%{specialization}%"))
    if mapped_specialization:
        filters.append(Doctor.specialization.ilike(f"%{mapped_specialization}%"))

    doctors_query = Doctor.query
    if filters:
        doctors_query = doctors_query.filter(or_(*filters))

    doctors = doctors_query.all()
    return [_serialize_doctor(doctor) for doctor in doctors]
