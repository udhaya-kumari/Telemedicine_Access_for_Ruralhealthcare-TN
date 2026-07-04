from flask import Blueprint, request, session

from extensions import db
from models import Appointment, Doctor, EmergencyRequest, Patient
from services.jitsi_service import generate_jitsi_link
from services.session_service import doctor_required, json_response, patient_required


emergency_bp = Blueprint("emergency", __name__)


def _current_patient():
    return Patient.query.filter_by(user_id=session["user_id"]).first()


def _current_doctor():
    return Doctor.query.filter_by(user_id=session["user_id"]).first()


def _serialize_doctor(doctor):
    return {
        "id": doctor.id,
        "name": getattr(doctor, "name", None),
        "specialization": getattr(doctor, "specialization", None),
        "hospital": getattr(doctor, "hospital", None),
        "location": getattr(doctor, "location", None),
    }


def _serialize_emergency(emergency):
    patient = Patient.query.get(emergency.patient_id)
    return {
        "id": emergency.id,
        "patient_id": emergency.patient_id,
        "patient_name": getattr(patient, "name", "Patient"),
        "patient_phone": getattr(patient, "phone", None),
        "symptoms": getattr(emergency, "symptoms", None),
        "description": getattr(emergency, "description", None),
        "location": getattr(emergency, "location", None),
        "contact_number": getattr(emergency, "contact_number", None) or getattr(emergency, "phone", None),
        "status": getattr(emergency, "status", None),
        "created_at": emergency.created_at.isoformat() if getattr(emergency, "created_at", None) else None,
    }


@emergency_bp.post("/emergency/request")
@patient_required
def emergency_request():
    patient = _current_patient()
    if not patient:
        return json_response(False, "not_found", status=404)

    data = request.get_json(silent=True) or request.form
    emergency = EmergencyRequest()
    emergency.patient_id = patient.id
    for field in ("description", "symptoms", "location", "contact_number"):
        if field in data and hasattr(emergency, field):
            setattr(emergency, field, data.get(field))
    if hasattr(emergency, "contact_number") and not getattr(emergency, "contact_number", None):
        emergency.contact_number = data.get("phone")
    if hasattr(emergency, "status"):
        emergency.status = "PENDING"

    db.session.add(emergency)
    db.session.commit()
    return json_response(True, "emergency_requested", {
        "request_id": emergency.id,
        "status": getattr(emergency, "status", "PENDING"),
    }, status=201)


@emergency_bp.get("/emergency/doctor-list")
@patient_required
def emergency_doctor_list():
    query = Doctor.query
    if hasattr(Doctor, "is_available"):
        query = query.filter_by(is_available=True)
    doctors = query.all()
    return json_response(True, data=[_serialize_doctor(doctor) for doctor in doctors])


@emergency_bp.get("/emergency/doctor/list")
@doctor_required
def emergency_doctor_requests():
    """Pending emergency alerts any doctor can pick up, used to power the
    red 'Emergency' card and alert list on the doctor dashboard."""
    emergencies = (
        EmergencyRequest.query.filter_by(status="PENDING")
        .order_by(EmergencyRequest.created_at.desc())
        .all()
    )
    return json_response(True, data=[_serialize_emergency(emergency) for emergency in emergencies])


@emergency_bp.post("/emergency/<int:emergency_id>/accept")
@doctor_required
def accept_emergency(emergency_id):
    doctor = _current_doctor()
    emergency = EmergencyRequest.query.get(emergency_id)
    if not doctor or not emergency:
        return json_response(False, "not_found", status=404)
    if emergency.status != "PENDING":
        return json_response(False, message="This emergency request has already been handled.", status=409)

    emergency.status = "ACCEPTED"
    if hasattr(emergency, "assigned_doctor_id"):
        emergency.assigned_doctor_id = doctor.id

    # Reuse the normal appointment + chat + video-call flow so the doctor
    # can immediately message/call the patient, without needing a slot.
    appointment = Appointment()
    appointment.patient_id = emergency.patient_id
    appointment.doctor_id = doctor.id
    appointment.status = "ACCEPTED"
    if hasattr(appointment, "reason"):
        appointment.reason = "Emergency: " + (emergency.symptoms or emergency.description or "").strip()
    db.session.add(appointment)
    db.session.flush()
    appointment.jitsi_link = generate_jitsi_link(appointment.id)
    db.session.commit()

    return json_response(True, message="Emergency accepted. A video consultation has been started.", data={
        "emergency_id": emergency.id,
        "appointment_id": appointment.id,
    })
