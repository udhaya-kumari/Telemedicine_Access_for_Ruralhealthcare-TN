from flask import Blueprint, current_app, request, session

from extensions import db
from models import Appointment, ChatMessage
from routes.appointment_routes import _current_doctor, _current_patient
from services.file_service import save_uploaded_file
from services.session_service import json_response, login_required


chat_bp = Blueprint("chat", __name__)


def _can_access_appointment(appointment):
    if session.get("role") == "Doctor":
        doctor = _current_doctor()
        return doctor and appointment.doctor_id == doctor.id
    if session.get("role") == "Patient":
        patient = _current_patient()
        return patient and appointment.patient_id == patient.id
    return False


def get_canonical_appointment_id(doctor_id, patient_id):
    """The id of the single, continuous chat thread for a doctor/patient pair.

    A doctor and patient may end up with several appointments over time
    (rebooked slots, follow-up visits, etc). Rather than starting a brand new
    chat for every appointment, all conversation history for a given
    doctor/patient pair lives on their earliest non-rejected appointment
    together, and every later appointment simply points back to it. A
    rejected appointment never started a real conversation, so it's skipped
    unless it's the only appointment the pair ever had.
    """
    base_query = Appointment.query.filter_by(doctor_id=doctor_id, patient_id=patient_id)

    first_appointment = (
        base_query.filter(Appointment.status != "REJECTED")
        .order_by(Appointment.created_at.asc(), Appointment.id.asc())
        .first()
    )
    if not first_appointment:
        first_appointment = base_query.order_by(Appointment.created_at.asc(), Appointment.id.asc()).first()

    return first_appointment.id if first_appointment else None


def get_latest_appointment(doctor_id, patient_id):
    """The most recently created appointment for a pair, used for live status
    (e.g. whether the video-call button should show) rather than message
    storage — that always lives on the canonical/oldest appointment."""
    return (
        Appointment.query.filter_by(doctor_id=doctor_id, patient_id=patient_id)
        .order_by(Appointment.created_at.desc(), Appointment.id.desc())
        .first()
    )


def resolve_conversation_appointment(appointment):
    """Given any appointment, return the appointment that actually holds the
    chat history for that doctor/patient pair (creating no new thread)."""
    if not appointment:
        return None
    canonical_id = get_canonical_appointment_id(appointment.doctor_id, appointment.patient_id)
    if canonical_id and canonical_id != appointment.id:
        return Appointment.query.get(canonical_id) or appointment
    return appointment


def _serialize_message(message):
    file_url = getattr(message, "file_url", None)
    text = getattr(message, "text", None) or getattr(message, "message", None)
    return {
        "id": message.id,
        "appointment_id": getattr(message, "appointment_id", None),
        "sender_id": getattr(message, "sender_id", None),
        "sender_role": getattr(message, "sender_role", None),
        "message": text,
        "text": text,
        "file_name": getattr(message, "file_name", None),
        "file_url": file_url,
        "attachment_url": file_url,
        "created_at": str(getattr(message, "created_at", "")),
    }


@chat_bp.get("/chat/messages/<int:appointment_id>")
@login_required
def chat_messages(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return json_response(False, "not_found", status=404)
    if not _can_access_appointment(appointment):
        return json_response(False, "unauthorized", status=403)

    # Always read from the pair's one continuous thread, even if this
    # particular appointment isn't the original one.
    thread_appointment = resolve_conversation_appointment(appointment)

    # But show the *live* status/video-link from the pair's most recent
    # appointment, so a new booking's "Join Consultation" button still works
    # correctly even though messages stay on the original thread.
    latest_appointment = get_latest_appointment(appointment.doctor_id, appointment.patient_id) or thread_appointment

    messages = (
        ChatMessage.query.filter_by(appointment_id=thread_appointment.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    data = [_serialize_message(message) for message in messages]
    meeting_link = getattr(latest_appointment, "jitsi_link", None)
    if meeting_link:
        data.append({
            "id": "jitsi-link",
            "appointment_id": latest_appointment.id,
            "sender_id": None,
            "sender_role": "System",
            "message": f"Video consultation link: {meeting_link}",
            "text": f"Video consultation link: {meeting_link}",
            "file_name": None,
            "file_url": None,
            "attachment_url": None,
            # The direct Jitsi room URL (e.g. https://meet.jit.si/TeleMed_42),
            # room id included, for the "Join Now" button.
            "meeting_link": meeting_link,
            "created_at": "",
        })
    return {
        "success": True,
        "current_user_id": session["user_id"],
        "appointment_status": getattr(latest_appointment, "status", None),
        # The chat thread (messages) always lives on the canonical/oldest
        # appointment, but joining a video call should use whichever
        # appointment is actually ACCEPTED right now.
        "video_appointment_id": getattr(latest_appointment, "id", None),
        # Direct Jitsi room link (contains the room id) for the top
        # "Join Consultation" button.
        "meeting_link": meeting_link,
        "messages": data,
        "data": data,
    }


@chat_bp.post("/chat/send")
@login_required
def send_message():
    data = request.form if request.form else request.get_json(silent=True) or {}
    appointment = Appointment.query.get(data.get("appointment_id"))
    if not appointment:
        return json_response(False, "not_found", status=404)
    if not _can_access_appointment(appointment):
        return json_response(False, "unauthorized", status=403)

    # Always write into the pair's one continuous thread so a new booking
    # never starts a separate chat from scratch.
    appointment = resolve_conversation_appointment(appointment)

    uploaded = None
    if "file" in request.files:
        uploaded = save_uploaded_file(
            request.files.get("file"),
            current_app.config["UPLOAD_FOLDER"],
            current_app.config["ALLOWED_EXTENSIONS"],
        )
        if not uploaded:
            return json_response(False, "invalid_file", status=400)

    message = ChatMessage()
    message.appointment_id = appointment.id
    message.sender_id = session["user_id"]
    if hasattr(message, "sender_role"):
        message.sender_role = session["role"]
    text = data.get("message") or data.get("text") or ""
    if hasattr(message, "message"):
        message.message = text
    if hasattr(message, "text"):
        message.text = text

    if uploaded:
        for field, value in {
            "file_name": uploaded["original_name"],
            "file_path": uploaded["file_path"],
            "file_url": uploaded["file_url"],
            "file_type": uploaded["file_type"],
        }.items():
            if hasattr(message, field):
                setattr(message, field, value)

    db.session.add(message)
    db.session.commit()
    return json_response(True, "message_sent", _serialize_message(message), status=201)
