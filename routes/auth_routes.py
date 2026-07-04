import re

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import check_password_hash

from extensions import db
from models import Doctor, Patient, User
from services.session_service import json_response, refresh_session_activity, translate

auth_bp = Blueprint("auth", __name__)

# At least 8 characters, one uppercase, one lowercase, one digit and one
# special character. Keeps weak/guessable passwords out at registration time.
PASSWORD_RULE_MESSAGE = (
    "Password must be at least 8 characters long and include an uppercase "
    "letter, a lowercase letter, a number, and a special character."
)


def _is_strong_password(password):
    if not password or len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[^A-Za-z0-9]", password):
        return False
    return True


def _request_payload():
    data = request.get_json(silent=True)
    if data:
        return data
    if request.form:
        return request.form.to_dict()
    return {}


def _wants_json_response():
    return (
        request.is_json
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in (request.headers.get("Accept") or "")
    )


def _password_matches(user, password):
    stored_password = getattr(user, "password_hash", None) or getattr(user, "password", None)
    if not stored_password:
        return False
    try:
        return check_password_hash(stored_password, password)
    except ValueError:
        return stored_password == password


def _auth_error(message, status=400):
    if _wants_json_response():
        return jsonify({"success": False, "message": message, "data": None}), status
    flash(message, "danger")
    return None


@auth_bp.post("/login")
def login():
    data = _request_payload()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return json_response(False, "missing_fields", status=400)

    try:
        user = User.query.filter_by(email=email).first()
    except SQLAlchemyError:
        db.session.rollback()
        return json_response(
            False,
            message="Unable to reach the database. Please ensure MySQL is running and configured.",
            status=503,
        )

    if not user or not _password_matches(user, password):
        return json_response(False, "invalid_credentials", status=401)

    session["user_id"] = user.id
    session["role"] = user.role
    session["name"] = user.name
    session["user"] = {
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "email": user.email,
    }
    refresh_session_activity()

    return jsonify({
        "success": True,
        "message": translate("login_success"),
        "role": user.role,
        "data": {"role": user.role},
    })


@auth_bp.post("/logout")
def logout():
    session.clear()
    return json_response(True, "logout_success")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    data = _request_payload()

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "").strip()
    phone = (data.get("phone") or "").strip() or None
    reg_no = (data.get("reg_no") or "").strip() or None

    if not name or not email or not password or role not in {"Patient", "Doctor"}:
        error = _auth_error("Please fill in all required fields.")
        if error:
            return error
        return redirect(url_for("auth.register"))

    if role == "Doctor" and not reg_no:
        error = _auth_error("Doctor registration number is required.")
        if error:
            return error
        return redirect(url_for("auth.register"))

    if not _is_strong_password(password):
        error = _auth_error(PASSWORD_RULE_MESSAGE)
        if error:
            return error
        return redirect(url_for("auth.register"))

    try:
        existing = User.query.filter(db.func.lower(User.email) == email).first()
        if existing:
            error = _auth_error("Email already registered.")
            if error:
                return error
            return redirect(url_for("auth.register"))

        if role == "Doctor":
            existing_reg_no = Doctor.query.filter(db.func.lower(Doctor.reg_no) == reg_no.lower()).first()
            if existing_reg_no:
                error = _auth_error("Doctor registration number already in use.")
                if error:
                    return error
                return redirect(url_for("auth.register"))

        user = User(
            name=name,
            email=email,
            phone=phone,
            role=role,
        )
        user.set_password(password)

        db.session.add(user)
        db.session.flush()

        if role == "Patient":
            db.session.add(Patient(user_id=user.id, name=name, phone=phone))
        elif role == "Doctor":
            db.session.add(Doctor(user_id=user.id, name=name, reg_no=reg_no))

        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        message = (
            "Doctor registration number already in use."
            if role == "Doctor"
            else "Email already registered."
        )
        error = _auth_error(message)
        if error:
            return error
        return redirect(url_for("auth.register"))
    except SQLAlchemyError:
        db.session.rollback()
        error = _auth_error(
            "Unable to save your account. Please ensure MySQL is running and the database schema is up to date."
        )
        if error:
            return error
        return redirect(url_for("auth.register"))

    if _wants_json_response():
        return jsonify({
            "success": True,
            "message": "Registration successful. Please login.",
            "data": None,
        })

    flash("Registration successful. Please login.", "success")
    return redirect(url_for("login"))
