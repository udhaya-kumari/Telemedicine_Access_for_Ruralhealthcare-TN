from flask import Blueprint, request, session

from extensions import db
from models import Appointment, Doctor, DoctorSlot, Patient
from services.jitsi_service import generate_jitsi_link
from services.session_service import doctor_required, json_response, login_required, patient_required


appointment_bp = Blueprint("appointment", __name__)


def _current_patient():
    return Patient.query.filter_by(user_id=session["user_id"]).first()


def _current_doctor():
    return Doctor.query.filter_by(user_id=session["user_id"]).first()


def _serialize_slot(slot):
    slot_date = getattr(slot, "date", None) or getattr(slot, "slot_date", None)
    start_time = getattr(slot, "start_time", None) or getattr(slot, "slot_time", None)
    end_time = getattr(slot, "end_time", None)
    return {
        "id": slot.id,
        "doctor_id": getattr(slot, "doctor_id", None),
        "date": str(slot_date or ""),
        "slot_date": str(slot_date or ""),
        "slot_time": str(start_time or ""),
        "start_time": str(start_time or ""),
        "end_time": str(end_time or ""),
        "status": getattr(slot, "status", None),
    }


def _serialize_appointment(appointment):
    return {
        "id": appointment.id,
        "patient_id": getattr(appointment, "patient_id", None),
        "doctor_id": getattr(appointment, "doctor_id", None),
        "slot_id": getattr(appointment, "slot_id", None),
        "status": getattr(appointment, "status", None),
        "reason": getattr(appointment, "reason", None),
        "jitsi_link": getattr(appointment, "jitsi_link", None),
    }


def _appointment_request_item(appointment):
    patient = Patient.query.get(getattr(appointment, "patient_id", None))
    slot = DoctorSlot.query.get(getattr(appointment, "slot_id", None))
    slot_data = _serialize_slot(slot) if slot else {}
    return {
        "id": appointment.id,
        "patient_id": getattr(appointment, "patient_id", None),
        "patient_name": getattr(patient, "name", "Patient"),
        "reason": getattr(appointment, "reason", None),
        "date": slot_data.get("date", ""),
        "start_time": slot_data.get("start_time", ""),
        "end_time": slot_data.get("end_time", ""),
        "status": getattr(appointment, "status", None),
    }


@appointment_bp.get("/appointments/available-slots/<int:doctor_id>")
@patient_required
def available_slots(doctor_id):
    slots = DoctorSlot.query.filter_by(doctor_id=doctor_id, status="AVAILABLE").all()
    return json_response(True, data=[_serialize_slot(slot) for slot in slots])


@appointment_bp.post("/appointment/book")
@patient_required
def book_appointment():
    patient = _current_patient()
    if not patient:
        return json_response(False, "not_found", status=404)

    data = request.get_json(silent=True) or request.form
    slot_id = data.get("slot_id")
    if not slot_id:
        return json_response(False, "missing_fields", status=400)

    slot = DoctorSlot.query.get(slot_id)
    if not slot or getattr(slot, "status", None) != "AVAILABLE":
        return json_response(False, "slot_not_available", status=409)

    appointment = Appointment()
    appointment.patient_id = patient.id
    appointment.doctor_id = slot.doctor_id
    appointment.slot_id = slot.id
    appointment.status = "PENDING"
    if hasattr(appointment, "reason"):
        appointment.reason = data.get("reason")

    slot.status = "BOOKED"
    db.session.add(appointment)
    db.session.commit()
    return json_response(True, "appointment_booked", _serialize_appointment(appointment), status=201)


@appointment_bp.post("/appointment/accept")
@doctor_required
def accept_appointment():
    doctor = _current_doctor()
    data = request.get_json(silent=True) or request.form
    appointment = Appointment.query.get(data.get("appointment_id"))
    if not doctor or not appointment:
        return json_response(False, "not_found", status=404)
    if appointment.doctor_id != doctor.id:
        return json_response(False, "unauthorized", status=403)

    appointment.status = "ACCEPTED"
    appointment.jitsi_link = generate_jitsi_link(appointment.id)
    db.session.commit()
    return json_response(True, "appointment_accepted", _serialize_appointment(appointment))


@appointment_bp.post("/appointment/reject")
@doctor_required
def reject_appointment():
    doctor = _current_doctor()
    data = request.get_json(silent=True) or request.form
    appointment = Appointment.query.get(data.get("appointment_id"))
    if not doctor or not appointment:
        return json_response(False, "not_found", status=404)
    if appointment.doctor_id != doctor.id:
        return json_response(False, "unauthorized", status=403)

    appointment.status = "REJECTED"
    slot = DoctorSlot.query.get(getattr(appointment, "slot_id", None))
    if slot and getattr(slot, "status", None) == "BOOKED":
        slot.status = "AVAILABLE"
    db.session.commit()
    return json_response(True, message="Appointment rejected.", data=_serialize_appointment(appointment))


@appointment_bp.post("/appointment/complete")
@doctor_required
def complete_appointment():
    doctor = _current_doctor()
    data = request.get_json(silent=True) or request.form
    appointment = Appointment.query.get(data.get("appointment_id"))
    if not doctor or not appointment:
        return json_response(False, "not_found", status=404)
    if appointment.doctor_id != doctor.id:
        return json_response(False, "unauthorized", status=403)

    appointment.status = "COMPLETED"
    db.session.commit()
    return json_response(True, message="Appointment marked as completed.", data=_serialize_appointment(appointment))


@appointment_bp.post("/appointment/change-slot")
@doctor_required
def change_slot():
    doctor = _current_doctor()
    data = request.get_json(silent=True) or request.form
    appointment = Appointment.query.get(data.get("appointment_id"))
    new_slot = DoctorSlot.query.get(data.get("new_slot_id")) if data.get("new_slot_id") else None

    if not doctor or not appointment:
        return json_response(False, "not_found", status=404)
    if appointment.doctor_id != doctor.id:
        return json_response(False, "unauthorized", status=403)
    if not new_slot:
        new_slot = DoctorSlot()
        new_slot.doctor_id = doctor.id
        new_slot.status = "AVAILABLE"
        for field, value in {
            "date": data.get("date"),
            "slot_date": data.get("date"),
            "start_time": data.get("start_time"),
            "slot_time": data.get("start_time"),
            "end_time": data.get("end_time"),
        }.items():
            if value and hasattr(new_slot, field):
                setattr(new_slot, field, value)
        db.session.add(new_slot)
        db.session.flush()
    if new_slot.doctor_id != doctor.id:
        return json_response(False, "unauthorized", status=403)
    if new_slot.status != "AVAILABLE":
        return json_response(False, "slot_not_available", status=409)

    old_slot = DoctorSlot.query.get(getattr(appointment, "slot_id", None))
    if old_slot:
        old_slot.status = "AVAILABLE"

    appointment.slot_id = new_slot.id
    appointment.status = "RESCHEDULED"
    new_slot.status = "BOOKED"
    db.session.commit()
    return json_response(True, "slot_changed", _serialize_appointment(appointment))


ACTIVE_REQUEST_STATUSES = ["PENDING", "ACCEPTED", "RESCHEDULED"]


@appointment_bp.get("/doctor/appointment-requests")
@doctor_required
def appointment_requests():
    doctor = _current_doctor()
    if not doctor:
        return [], 404
    # Only actionable/current requests here (not old completed or rejected ones,
    # which aren't "requests" anymore). Completed history is available via each
    # patient's own history page.
    appointments = (
        Appointment.query.filter_by(doctor_id=doctor.id)
        .filter(Appointment.status.in_(ACTIVE_REQUEST_STATUSES))
        .order_by(Appointment.created_at.desc())
        .all()
    )
    return [_appointment_request_item(appointment) for appointment in appointments]


@appointment_bp.get("/consultation/<int:appointment_id>/meeting")
@login_required
def consultation_meeting(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return {"meeting_link": None, "display_name": "TeleMed user"}, 404

    role = session.get("role")
    allowed = False
    display_name = "TeleMed user"
    if role == "Doctor":
        doctor = _current_doctor()
        allowed = bool(doctor and appointment.doctor_id == doctor.id)
        display_name = getattr(doctor, "name", display_name) if doctor else display_name
    elif role == "Patient":
        patient = _current_patient()
        allowed = bool(patient and appointment.patient_id == patient.id)
        display_name = getattr(patient, "name", display_name) if patient else display_name

    if not allowed:
        return {"meeting_link": None, "display_name": display_name}, 403
    if not getattr(appointment, "jitsi_link", None):
        appointment.jitsi_link = generate_jitsi_link(appointment.id)
        db.session.commit()
    return {"meeting_link": appointment.jitsi_link, "display_name": display_name}
