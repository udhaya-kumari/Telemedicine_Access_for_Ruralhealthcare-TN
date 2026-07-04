from flask import Flask, jsonify, redirect, render_template, send_from_directory, session, url_for
from werkzeug.exceptions import HTTPException

from config import Config
from extensions import cors, db
from models import Appointment
from routes.appointment_routes import appointment_bp, _current_doctor
from routes.auth_routes import auth_bp
from routes.chat_routes import chat_bp, get_canonical_appointment_id
from routes.consult_routes import consult_bp
from routes.doctor_routes import doctor_bp
from routes.emergency_routes import emergency_bp
from routes.medical_routes import medical_bp
from routes.patient_routes import patient_bp, patient_for_current_user
from routes.search_routes import search_bp
from services.file_service import ensure_upload_folder
from services.seed_service import seed_sample_data
from services.session_service import page_login_required



def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    ensure_upload_folder(app.config["UPLOAD_FOLDER"])

    db.init_app(app)
    cors.init_app(app, supports_credentials=True)

    app.register_blueprint(auth_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(appointment_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(medical_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(emergency_bp)
    app.register_blueprint(consult_bp)

    @app.route("/health")
    def health_check():
        return jsonify({"success": True, "message": "API is running", "data": None})

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.get("/login")
    def login():
        if session.get("user_id"):
            role = session.get("role")
            if role == "Doctor":
                return redirect(url_for("doctor_dashboard"))
            elif role == "Patient":
                return redirect(url_for("patient_dashboard"))
        return render_template("login.html")

    @app.get("/doctor/dashboard")
    @page_login_required
    def doctor_dashboard():
        if session.get("role") != "Doctor":
            return redirect(url_for("patient_dashboard"))
        return render_template("doctor_dashboard.html")

    @app.get("/patient/dashboard")
    @page_login_required
    def patient_dashboard():
        if session.get("role") != "Patient":
            return redirect(url_for("doctor_dashboard"))
        return render_template("patient_dashboard.html")

    @app.get("/profile")
    @page_login_required
    def profile():
        return render_template("profile.html")

    @app.get("/appointments")
    @page_login_required
    def appointments():
        return render_template("appointment.html")

    @app.get("/doctor/slots")
    @page_login_required
    def doctor_slots_page():
        return render_template("slots.html")

    @app.get("/doctor/patients")
    @page_login_required
    def doctor_patients_page():
        if session.get("role") != "Doctor":
            return redirect(url_for("patient_dashboard"))

        doctor = _current_doctor()
        patients = []
        if doctor:
            appointments = (
                Appointment.query.filter_by(doctor_id=doctor.id)
                .order_by(Appointment.created_at.desc())
                .all()
            )
            seen = {}
            for appointment in appointments:
                patient = appointment.patient
                if not patient or patient.id in seen:
                    continue
                slot = appointment.slot
                slot_date = getattr(slot, "date", None) or getattr(slot, "slot_date", None) if slot else ""
                seen[patient.id] = {
                    "id": patient.id,
                    "name": patient.name,
                    "age": patient.age,
                    "gender": patient.gender,
                    "village": patient.village,
                    "last_date": slot_date or "",
                    "last_status": appointment.status,
                    "last_appointment_id": appointment.id,
                }
            patients = list(seen.values())
        return render_template("doctor_patients.html", patients=patients)

    @app.get("/patient/records")
    @page_login_required
    def patient_records_page():
        return render_template("records.html", records=[])

    @app.get("/emergency")
    @page_login_required
    def emergency_page():
        return render_template("emergency.html")

    @app.get("/doctor/emergencies")
    @page_login_required
    def doctor_emergencies_page():
        if session.get("role") != "Doctor":
            return redirect(url_for("patient_dashboard"))
        return render_template("doctor_emergencies.html")

    @app.get("/chat")
    @app.get("/chat/<int:appointment_id>")
    @page_login_required
    def chat(appointment_id=None):
        role = session.get("role")

        # If we've landed on a specific appointment's chat, make sure we're
        # looking at the one continuous thread for that doctor/patient pair
        # instead of a fresh, empty one — same pair always means same chat.
        if appointment_id:
            appointment = Appointment.query.get(appointment_id)
            if appointment:
                canonical_id = get_canonical_appointment_id(appointment.doctor_id, appointment.patient_id)
                if canonical_id and canonical_id != appointment_id:
                    return redirect(url_for("chat", appointment_id=canonical_id))

        chats = []
        if not appointment_id:
            appointments = []
            if role == "Doctor":
                doctor = _current_doctor()
                if doctor:
                    appointments = (
                        Appointment.query.filter_by(doctor_id=doctor.id)
                        .filter(Appointment.status != "REJECTED")
                        .order_by(Appointment.created_at.desc())
                        .all()
                    )
            elif role == "Patient":
                patient = patient_for_current_user()
                if patient:
                    appointments = (
                        Appointment.query.filter_by(patient_id=patient.id)
                        .filter(Appointment.status != "REJECTED")
                        .order_by(Appointment.created_at.desc())
                        .all()
                    )

            # Group every appointment by the other party so a doctor/patient
            # pair shows up as a single ongoing conversation, not one row per
            # booking. The oldest appointment in each group is where all of
            # that pair's messages actually live.
            grouped = {}
            for appointment in appointments:
                counterpart_id = appointment.patient_id if role == "Doctor" else appointment.doctor_id
                grouped.setdefault(counterpart_id, []).append(appointment)

            for counterpart_id, group_appointments in grouped.items():
                canonical = min(group_appointments, key=lambda a: (a.created_at, a.id))
                latest = max(group_appointments, key=lambda a: (a.created_at, a.id))
                if role == "Doctor":
                    other_name = f"{latest.patient.name}" if latest.patient else "Patient"
                else:
                    other_name = f"Dr. {latest.doctor.name}" if latest.doctor else "Doctor"
                chats.append({
                    "appointment_id": canonical.id,
                    "other_party_name": other_name,
                    "status": latest.status,
                })
            chats.sort(key=lambda c: (c["other_party_name"] or "").lower())

        return render_template("chat.html", appointment_id=appointment_id, chats=chats)

    @app.get("/consultation/<int:appointment_id>")
    @page_login_required
    def consultation(appointment_id):
        return render_template("consultation.html", appointment_id=appointment_id)

    @app.get("/patient/history")
    @page_login_required
    def patient_history():
        history = []
        if session.get("role") == "Patient":
            patient = patient_for_current_user()
            if patient:
                appointments = (
                    Appointment.query.filter_by(patient_id=patient.id)
                    .order_by(Appointment.created_at.desc())
                    .all()
                )
                for appointment in appointments:
                    slot = appointment.slot
                    slot_date = getattr(slot, "date", None) or getattr(slot, "slot_date", None) if slot else ""
                    slot_time = getattr(slot, "start_time", None) or getattr(slot, "slot_time", None) if slot else ""
                    history.append({
                        "id": appointment.id,
                        "date": slot_date or "",
                        "time": slot_time or "",
                        "other_party_name": f"Dr. {appointment.doctor.name}" if appointment.doctor else "",
                        "status": appointment.status,
                        "prescription_url": None,
                    })
        return render_template("history.html", history=history)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({
            "success": False,
            "message": error.description,
            "data": None,
        }), error.code

    @app.errorhandler(Exception)
    def handle_error(error):
        app.logger.exception(error)
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Something went wrong. Please try again.",
            "data": None,
        }), 500

    @app.after_request
    def add_no_cache_headers(response):
        if session.get("user_id"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app


app = create_app()


def init_database():
    with app.app_context():
        db.create_all()
        seed_sample_data()


try:
    init_database()
except Exception as error:
    app.logger.error("Database initialization failed: %s", error)


if __name__ == "__main__":
    # "adhoc" auto-generates a temporary self-signed certificate so the app
    # is served over HTTPS. This matters for camera/mic access in the video
    # consultation: browsers only allow getUserMedia() over HTTPS (or
    # localhost), so opening the app from a phone via the LAN IP over plain
    # HTTP silently blocks Jitsi's camera/mic prompt.
    #
    # Requires the `pyopenssl` package: pip install pyopenssl
    #
    # Visiting the https:// LAN address on your phone will show a
    # "connection not private" warning because the cert is self-signed —
    # this is expected for local testing; tap Advanced -> Proceed.
    app.run(host="0.0.0.0", port=5000, debug=True, ssl_context="adhoc")
