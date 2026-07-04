from datetime import datetime, timedelta
from functools import wraps

from flask import jsonify, redirect, request, session, url_for


SESSION_TIMEOUT = timedelta(hours=12)


MESSAGES = {
    "en": {
        "login_required": "Please login to continue.",
        "doctor_required": "Doctor access required.",
        "patient_required": "Patient access required.",
        "session_expired": "Session expired. Please login again.",
        "invalid_credentials": "Invalid username or password.",
        "login_success": "Login successful.",
        "logout_success": "Logout successful.",
        "profile_updated": "Profile updated successfully.",
        "slot_added": "Slot added successfully.",
        "appointment_booked": "Appointment booked successfully.",
        "appointment_accepted": "Appointment accepted and video link generated.",
        "slot_changed": "Appointment slot changed successfully.",
        "message_sent": "Message sent successfully.",
        "record_uploaded": "Medical record uploaded successfully.",
        "emergency_requested": "Emergency request sent successfully.",
        "not_found": "Requested data not found.",
        "invalid_file": "Only PDF, JPG and PNG files are allowed.",
        "slot_not_available": "Selected slot is not available.",
        "unauthorized": "You are not allowed to access this data.",
        "missing_fields": "Required fields are missing.",
    },
    "ta": {
        "login_required": "தொடர உள்நுழையவும்.",
        "doctor_required": "மருத்துவர் அணுகல் தேவை.",
        "patient_required": "நோயாளர் அணுகல் தேவை.",
        "session_expired": "அமர்வு காலாவதியானது. மீண்டும் உள்நுழையவும்.",
        "invalid_credentials": "பயனர்பெயர் அல்லது கடவுச்சொல் தவறானது.",
        "login_success": "உள்நுழைவு வெற்றிகரமாக முடிந்தது.",
        "logout_success": "வெற்றிகரமாக வெளியேறிவிட்டீர்கள்.",
        "profile_updated": "சுயவிவரம் வெற்றிகரமாக புதுப்பிக்கப்பட்டது.",
        "slot_added": "நேரம் வெற்றிகரமாக சேர்க்கப்பட்டது.",
        "appointment_booked": "முன்பதிவு வெற்றிகரமாக முடிந்தது.",
        "appointment_accepted": "முன்பதிவு ஏற்றுக்கொள்ளப்பட்டது, வீடியோ இணைப்பு உருவாக்கப்பட்டது.",
        "slot_changed": "முன்பதிவு நேரம் வெற்றிகரமாக மாற்றப்பட்டது.",
        "message_sent": "செய்தி வெற்றிகரமாக அனுப்பப்பட்டது.",
        "record_uploaded": "மருத்துவ பதிவு வெற்றிகரமாக பதிவேற்றப்பட்டது.",
        "emergency_requested": "அவசர கோரிக்கை வெற்றிகரமாக அனுப்பப்பட்டது.",
        "not_found": "தேவையான தகவல் கிடைக்கவில்லை.",
        "invalid_file": "PDF, JPG மற்றும் PNG கோப்புகள் மட்டும் அனுமதிக்கப்படும்.",
        "slot_not_available": "தேர்ந்தெடுத்த நேரம் கிடைக்கவில்லை.",
        "unauthorized": "இந்த தகவலை அணுக உங்களுக்கு அனுமதி இல்லை.",
        "missing_fields": "தேவையான புலங்கள் விடுபட்டுள்ளன.",
    },
}


def current_language():
    data = request.get_json(silent=True) or {}
    language = data.get("language") or request.form.get("language") or request.args.get("language")
    if language in MESSAGES:
        session["language"] = language
    return session.get("language", "en")


def translate(key):
    language = current_language()
    return MESSAGES.get(language, MESSAGES["en"]).get(key, key)


def json_response(success=True, message_key=None, data=None, status=200, message=None):
    text = message if message is not None else translate(message_key) if message_key else ""
    return jsonify({"success": success, "message": text, "data": data}), status


def _session_is_expired():
    last_activity = session.get("last_activity")
    if not last_activity:
        return False
    try:
        last_seen = datetime.fromisoformat(last_activity)
    except ValueError:
        return True
    return datetime.utcnow() - last_seen > SESSION_TIMEOUT


def refresh_session_activity():
    session["last_activity"] = datetime.utcnow().isoformat()
    session.permanent = True


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return json_response(False, "login_required", status=401)
        if _session_is_expired():
            session.clear()
            return json_response(False, "session_expired", status=401)
        refresh_session_activity()
        return view(*args, **kwargs)

    return wrapped


def page_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if _session_is_expired():
            session.clear()
            return redirect(url_for("login"))
        refresh_session_activity()
        return view(*args, **kwargs)

    return wrapped


def doctor_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get("role") != "Doctor":
            return json_response(False, "doctor_required", status=403)
        return view(*args, **kwargs)

    return wrapped


def patient_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get("role") != "Patient":
            return json_response(False, "patient_required", status=403)
        return view(*args, **kwargs)

    return wrapped
