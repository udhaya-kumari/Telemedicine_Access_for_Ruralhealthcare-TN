TELEMEDICINE ACCESS FOR RURAL HEALTHCARE IN TAMILNADU
# TeleMed Tamil Nadu

A bilingual telemedicine web application developed for rural healthcare access in Tamil Nadu. The platform enables patients and doctors to connect through online consultations, appointment scheduling, secure medical record management, real-time chat, and Jitsi-based video consultations.

## Features

### Authentication & Security

* Role-based authentication (Doctor and Patient)
* Flask session-based authentication (No JWT)
* Automatic session expiry after 12 hours of inactivity
* Password hashing and secure login
* Protected routes using role-based access control

### Bilingual Support

* English and Tamil language selection
* Language preference stored in session
* User-friendly interface for rural healthcare users

### Doctor Management

* Doctor profile management
* Qualification, specialization, hospital, experience, and location details
* Doctor availability management
* Time slot creation and scheduling

### Patient Management

* Patient profile management
* Medical history storage
* Upload and manage medical documents
* Health record maintenance

### Medical Records

Supported file uploads:

* PDF reports
* X-Ray images
* CT Scan images
* CBC Reports
* JPG and PNG files

### Appointment Booking System

* Doctors create available time slots
* Patients view available slots
* Patients book appointments
* Doctors accept appointments
* Doctors can modify appointment timings
* Booked slots become unavailable automatically
* Automatic appointment confirmation

### Doctor Search

Search doctors by:

* Doctor name
* Specialty
* Symptoms

Example:

* Skin irritation → Dermatologist
* Fever → General Physician

### Chat System

* AJAX polling based real-time messaging
* No page refresh required
* Text messaging
* File sharing (PDF, JPG, PNG)
* Consultation link sharing
* Lightweight implementation

Not Included:

* Typing indicators
* Double tick/read receipts
* Message status tracking

### Video Consultation

* Jitsi Meet IFrame API integration
* Automatic meeting link generation
* Secure consultation rooms
* One-click consultation joining

Generated meeting format:

https://meet.jit.si/TeleMed_<appointment_id>

### Emergency Consultation

* Emergency consultation requests
* Available doctors receive emergency requests
* Quick doctor-patient connection

---

## Technology Stack

### Frontend

* HTML5
* CSS3
* Bootstrap 5
* JavaScript (Vanilla JS)
* AJAX (Fetch API)

### Backend

* Python
* Flask

### Database

* MySQL
* SQLAlchemy ORM

### Video Conferencing

* Jitsi Meet IFrame API

### Authentication

* Flask Session Authentication

---

## Project Structure

```text
telemed/

├── app.py
├── config.py
├── extensions.py
│
├── routes/
│   ├── auth_routes.py
│   ├── doctor_routes.py
│   ├── patient_routes.py
│   ├── appointment_routes.py
│   ├── medical_routes.py
│   ├── chat_routes.py
│   ├── search_routes.py
│   └── emergency_routes.py
│
├── services/
│   ├── jitsi_service.py
│   ├── file_service.py
│   └── session_service.py
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── patient_dashboard.html
│   ├── doctor_dashboard.html
│   ├── appointments.html
│   ├── chat.html
│   └── consultation.html
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── uploads/
│
└── models.py
```

---

## Main Modules

### Doctor Module

* Profile management
* Availability management
* Appointment handling
* Patient communication

### Patient Module

* Profile management
* Medical records
* Appointment booking
* Consultation participation

### Appointment Module

* Slot management
* Booking system
* Appointment confirmation
* Consultation scheduling

### Chat Module

* Real-time messaging
* File sharing
* Consultation link sharing

### Consultation Module

* Jitsi video consultation
* Follow-up consultations

---

## Database Entities

* User
* Doctor
* Patient
* DoctorSlot
* Appointment
* MedicalRecord
* ChatMessage
* EmergencyRequest

---

## Security Features

* Session-based authentication
* Role-based authorization
* Password hashing
* File type validation
* Session timeout protection
* Secure file uploads

---

## Future Enhancements

* SMS notifications
* Email notifications
* AI-assisted symptom analysis
* Prescription generation
* Mobile application support
* PHC integration
* Multi-doctor consultation

---

