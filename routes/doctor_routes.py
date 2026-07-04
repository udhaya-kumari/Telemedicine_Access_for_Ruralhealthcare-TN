from flask import Blueprint, render_template, request, session
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import Doctor, DoctorSlot
from services.session_service import doctor_required, json_response, patient_required


doctor_bp = Blueprint("doctor", __name__)


PROFILE_FIELDS = [
    "name",
    "reg_no",
    "qualification",
    "specialization",
    "hospital",
    "experience",
    "location",
    "consultation_fee",
]


def _doctor_for_current_user():
    return Doctor.query.filter_by(user_id=session["user_id"]).first()


def _serialize_doctor(doctor):
    return {field: getattr(doctor, field, None) for field in ["id", "user_id", *PROFILE_FIELDS]}


def _serialize_slot(slot):
    slot_date = getattr(slot, "date", None) or getattr(slot, "slot_date", None)
    start_time = getattr(slot, "start_time", None) or getattr(slot, "slot_time", None)
    end_time = getattr(slot, "end_time", None)
    status = getattr(slot, "status", None)
    return {
        "id": slot.id,
        "doctor_id": getattr(slot, "doctor_id", None),
        "date": str(slot_date or ""),
        "slot_date": str(slot_date or ""),
        "slot_time": str(start_time or ""),
        "start_time": str(start_time or ""),
        "end_time": str(end_time or ""),
        "status": status,
        "booked": str(status or "").upper() == "BOOKED",
    }


@doctor_bp.get("/doctor/profile")
@doctor_required
def doctor_profile():
    doctor = _doctor_for_current_user()
    if not doctor:
        return json_response(False, "not_found", status=404)
    return _serialize_doctor(doctor)


@doctor_bp.post("/doctor/profile/update")
@doctor_required
def update_doctor_profile():
    doctor = _doctor_for_current_user()
    if not doctor:
        return json_response(False, "not_found", status=404)

    data = request.get_json(silent=True) or request.form
    for field in PROFILE_FIELDS:
        if field not in data or not hasattr(doctor, field):
            continue
        value = data.get(field)
        if field == "consultation_fee":
            # Optional field: blank clears it, otherwise store as a number.
            if value in (None, ""):
                value = None
            else:
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    return json_response(False, "invalid_consultation_fee", status=400)
        if field == "reg_no":
            value = (value or "").strip() or None
            if value:
                duplicate = Doctor.query.filter(
                    Doctor.reg_no == value, Doctor.id != doctor.id
                ).first()
                if duplicate:
                    return json_response(
                        False, message="Doctor registration number already in use.", status=409
                    )
        setattr(doctor, field, value)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return json_response(
            False, message="Doctor registration number already in use.", status=409
        )

    data = _serialize_doctor(doctor)
    return {"success": True, "message": "Profile updated successfully.", "data": data, **data}


@doctor_bp.post("/doctor/add-slot")
@doctor_required
def add_slot():
    doctor = _doctor_for_current_user()
    if not doctor:
        return json_response(False, "not_found", status=404)

    data = request.get_json(silent=True) or request.form
    slot = DoctorSlot()
    slot.doctor_id = doctor.id
    slot.status = data.get("status", "AVAILABLE")

    field_map = {
        "date": ["date", "slot_date"],
        "slot_date": ["slot_date", "date"],
        "slot_time": ["slot_time", "start_time"],
        "start_time": ["start_time", "slot_time"],
        "end_time": ["end_time"],
    }
    for field, aliases in field_map.items():
        if field in data and hasattr(slot, field):
            setattr(slot, field, data.get(field))
        elif hasattr(slot, field):
            for alias in aliases:
                if alias in data:
                    setattr(slot, field, data.get(alias))
                    break

    db.session.add(slot)
    db.session.commit()
    return json_response(True, "slot_added", _serialize_slot(slot), status=201)


@doctor_bp.get("/doctor/slots")
@doctor_required
def doctor_slots():
    if "text/html" in request.headers.get("Accept", ""):
        return render_template("slots.html")
    doctor = _doctor_for_current_user()
    if not doctor:
        return json_response(False, "not_found", status=404)
    slots = DoctorSlot.query.filter_by(doctor_id=doctor.id).all()
    return json_response(True, data=[_serialize_slot(slot) for slot in slots])


@doctor_bp.get("/doctor/slots/list")
@doctor_required
def doctor_slots_list():
    doctor = _doctor_for_current_user()
    if not doctor:
        return {"slots": []}, 404
    slots = DoctorSlot.query.filter_by(doctor_id=doctor.id).all()
    return {"slots": [_serialize_slot(slot) for slot in slots]}


@doctor_bp.get("/doctor/<int:doctor_id>/slots")
@patient_required
def public_doctor_slots(doctor_id):
    slots = DoctorSlot.query.filter_by(doctor_id=doctor_id).all()
    return [_serialize_slot(slot) for slot in slots]


@doctor_bp.post("/doctor/slots/delete/<int:slot_id>")
@doctor_required
def delete_slot(slot_id):
    doctor = _doctor_for_current_user()
    slot = DoctorSlot.query.get(slot_id)
    if not doctor or not slot:
        return json_response(False, "not_found", status=404)
    if slot.doctor_id != doctor.id:
        return json_response(False, "unauthorized", status=403)
    if getattr(slot, "status", None) == "BOOKED":
        return json_response(False, message="Booked slots cannot be deleted.", status=409)
    db.session.delete(slot)
    db.session.commit()
    return json_response(True, message="Slot deleted successfully.")
