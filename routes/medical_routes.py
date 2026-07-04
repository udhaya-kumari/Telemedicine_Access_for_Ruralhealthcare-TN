import os

from flask import Blueprint, current_app, render_template, request, session

from extensions import db
from models import MedicalRecord
from routes.patient_routes import patient_for_current_user
from services.file_service import save_uploaded_file
from services.session_service import json_response, patient_required


medical_bp = Blueprint("medical", __name__)


def _serialize_record(record):
    return {
        "id": record.id,
        "patient_id": getattr(record, "patient_id", None),
        "appointment_id": getattr(record, "appointment_id", None),
        "title": getattr(record, "title", None),
        "description": getattr(record, "description", None),
        "file_name": getattr(record, "file_name", None),
        "file_path": getattr(record, "file_path", None),
        "file_url": getattr(record, "file_url", None),
        "url": getattr(record, "file_url", None),
        "uploaded_at": str(getattr(record, "created_at", "")),
        "created_at": str(getattr(record, "created_at", "")),
    }


@medical_bp.post("/patient/upload-record")
@medical_bp.post("/patient/records/upload")
@patient_required
def upload_record():
    patient = patient_for_current_user()
    if not patient:
        return json_response(False, "not_found", status=404)

    uploaded = save_uploaded_file(
        request.files.get("file"),
        current_app.config["UPLOAD_FOLDER"],
        current_app.config["ALLOWED_EXTENSIONS"],
    )
    if not uploaded:
        return json_response(False, "invalid_file", status=400)

    record = MedicalRecord()
    record.patient_id = patient.id
    for field, value in {
        "appointment_id": request.form.get("appointment_id"),
        "title": request.form.get("title") or uploaded["original_name"],
        "description": request.form.get("description"),
        "file_name": uploaded["original_name"],
        "file_path": uploaded["file_path"],
        "file_url": uploaded["file_url"],
        "file_type": uploaded["file_type"],
    }.items():
        if hasattr(record, field):
            setattr(record, field, value)

    db.session.add(record)
    db.session.commit()
    return json_response(True, "record_uploaded", _serialize_record(record), status=201)


@medical_bp.get("/patient/records")
@patient_required
def patient_records():
    if "text/html" in request.headers.get("Accept", ""):
        return render_template("records.html", records=[])
    patient = patient_for_current_user()
    if not patient:
        return json_response(False, "not_found", status=404)

    records = MedicalRecord.query.filter_by(patient_id=patient.id).order_by(MedicalRecord.id.desc()).all()
    return json_response(True, data=[_serialize_record(record) for record in records])


@medical_bp.get("/patient/records/list")
@patient_required
def patient_records_list():
    patient = patient_for_current_user()
    if not patient:
        return {"records": []}, 404
    records = MedicalRecord.query.filter_by(patient_id=patient.id).order_by(MedicalRecord.id.desc()).all()
    return {"records": [_serialize_record(record) for record in records]}


@medical_bp.post("/patient/records/delete/<int:record_id>")
@patient_required
def delete_record(record_id):
    patient = patient_for_current_user()
    record = MedicalRecord.query.get(record_id)
    if not patient or not record:
        return json_response(False, "not_found", status=404)
    if record.patient_id != patient.id:
        return json_response(False, "unauthorized", status=403)

    file_path = getattr(record, "file_path", None)
    db.session.delete(record)
    db.session.commit()
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    return json_response(True, message="Medical record deleted successfully.")
