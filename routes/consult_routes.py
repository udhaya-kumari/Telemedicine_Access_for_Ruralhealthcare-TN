from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import or_

from extensions import db
from models import Appointment, Doctor, DoctorSlot
from routes.patient_routes import patient_for_current_user
from services.session_service import patient_required


consult_bp = Blueprint("consult", __name__)


def _today_str():
    return date.today().isoformat()


def _upcoming_slots_for_doctor(doctor_id):
    """All slots for a doctor from today onward, ordered by date/time."""
    today = _today_str()
    slots = DoctorSlot.query.filter_by(doctor_id=doctor_id).all()

    def slot_date(slot):
        return getattr(slot, "date", None) or getattr(slot, "slot_date", None) or ""

    def slot_time(slot):
        return getattr(slot, "start_time", None) or getattr(slot, "slot_time", None) or ""

    upcoming = [s for s in slots if slot_date(s) >= today]
    upcoming.sort(key=lambda s: (slot_date(s), slot_time(s)))
    return upcoming


@consult_bp.get("/consult-doctor")
@patient_required
def consult_doctor():
    query = (request.args.get("q") or "").strip()
    specialization = (request.args.get("specialization") or "").strip()
    available_today = request.args.get("available_today") == "on"

    doctors_query = Doctor.query.filter(Doctor.is_available.is_(True))

    if query:
        like = f"%{query}%"
        doctors_query = doctors_query.filter(
            or_(
                Doctor.name.ilike(like),
                Doctor.specialization.ilike(like),
                Doctor.symptoms_treated.ilike(like),
            )
        )

    if specialization:
        doctors_query = doctors_query.filter(Doctor.specialization == specialization)

    doctors = doctors_query.order_by(Doctor.name.asc()).all()

    if available_today:
        today = _today_str()
        filtered = []
        for doctor in doctors:
            has_today_slot = DoctorSlot.query.filter_by(
                doctor_id=doctor.id, status="AVAILABLE"
            ).filter(
                or_(DoctorSlot.date == today, DoctorSlot.slot_date == today)
            ).first()
            if has_today_slot:
                filtered.append(doctor)
        doctors = filtered

    specializations = [
        row[0]
        for row in db.session.query(Doctor.specialization)
        .filter(Doctor.specialization.isnot(None))
        .distinct()
        .order_by(Doctor.specialization.asc())
        .all()
    ]

    return render_template(
        "consult_doctor.html",
        doctors=doctors,
        query=query,
        specialization=specialization,
        available_today=available_today,
        specializations=specializations,
    )


@consult_bp.get("/consult-doctor/<int:doctor_id>/profile")
@patient_required
def doctor_profile_view(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    return render_template("doctor_profile_view.html", doctor=doctor)


@consult_bp.route("/consult-doctor/<int:doctor_id>/book", methods=["GET", "POST"])
@patient_required
def book_doctor_appointment(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    patient = patient_for_current_user()

    if request.method == "POST":
        if not patient:
            flash("Please complete your patient profile before booking.", "danger")
            return redirect(url_for("consult.book_doctor_appointment", doctor_id=doctor.id))

        slot_id = request.form.get("slot_id")
        reason = (request.form.get("reason") or "").strip()

        if not slot_id:
            flash("Please choose an available time slot.", "danger")
            return redirect(url_for("consult.book_doctor_appointment", doctor_id=doctor.id))

        slot = DoctorSlot.query.get(slot_id)
        today = _today_str()
        slot_date = getattr(slot, "date", None) or getattr(slot, "slot_date", None) or ""

        if not slot or slot.doctor_id != doctor.id:
            flash("Selected slot could not be found.", "danger")
        elif (slot.status or "AVAILABLE").upper() != "AVAILABLE":
            flash("That slot has already been booked. Please choose another.", "danger")
        elif slot_date < today:
            flash("You cannot book a slot in the past.", "danger")
        else:
            # Prevent a duplicate booking of the same slot by the same patient.
            existing = Appointment.query.filter_by(
                patient_id=patient.id, slot_id=slot.id
            ).filter(Appointment.status != "REJECTED").first()
            if existing:
                flash("You already have a booking for this slot.", "warning")
            else:
                appointment = Appointment()
                appointment.patient_id = patient.id
                appointment.doctor_id = doctor.id
                appointment.slot_id = slot.id
                appointment.status = "PENDING"
                appointment.reason = reason
                slot.status = "BOOKED"
                db.session.add(appointment)
                db.session.commit()
                flash("Appointment booked successfully. Status: Pending.", "success")
                return redirect(url_for("patient_history"))

        return redirect(url_for("consult.book_doctor_appointment", doctor_id=doctor.id))

    slots = _upcoming_slots_for_doctor(doctor.id)
    slots_by_date = {}
    for slot in slots:
        slot_date = getattr(slot, "date", None) or getattr(slot, "slot_date", None) or ""
        slots_by_date.setdefault(slot_date, []).append(slot)

    return render_template(
        "book_appointment.html",
        doctor=doctor,
        slots_by_date=slots_by_date,
    )
