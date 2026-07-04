from flask import Blueprint, request, session

from extensions import db
from models import Patient
from services.session_service import json_response, patient_required


patient_bp = Blueprint("patient", __name__)


PROFILE_FIELDS = ["name", "age", "gender", "phone", "blood_group", "address", "village", "district", "location"]


def patient_for_current_user():
    return Patient.query.filter_by(user_id=session["user_id"]).first()


def serialize_patient(patient):
    return {field: getattr(patient, field, None) for field in ["id", "user_id", *PROFILE_FIELDS]}


@patient_bp.get("/patient/profile")
@patient_required
def patient_profile():
    patient = patient_for_current_user()
    if not patient:
        return json_response(False, "not_found", status=404)
    return serialize_patient(patient)


@patient_bp.post("/patient/profile/update")
@patient_required
def update_patient_profile():
    patient = patient_for_current_user()
    if not patient:
        return json_response(False, "not_found", status=404)

    data = request.get_json(silent=True) or request.form
    for field in PROFILE_FIELDS:
        if field in data and hasattr(patient, field):
            setattr(patient, field, data.get(field))

    db.session.commit()
    data = serialize_patient(patient)
    return {"success": True, "message": "Profile updated successfully.", "data": data, **data}
