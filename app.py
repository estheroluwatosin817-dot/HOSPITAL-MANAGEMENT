from datetime import datetime
from functools import wraps
import os
import sqlite3
from flask import Flask, g, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.config["SECRET_KEY"] = "kiitan-health-care-secret"
app.config["DATABASE"] = os.path.join(app.root_path, "hospital.db")
VALID_LOGINS = {
    "esther": "okeleye123",
    "okeleye": "esther",
    "estherokeleye": "healthcare",
}

DEPARTMENTS = [
    "General Medicine",
    "Family Medicine",
    "Internal Medicine",
    "Pediatrics",
    "Obstetrics & Gynecology",
    "Cardiology",
    "Dermatology",
    "Endocrinology",
    "Gastroenterology",
    "Neurology",
    "Oncology",
    "Orthopedics",
    "Psychiatry",
    "Radiology",
    "Emergency Medicine",
    "Anesthesiology",
    "Ophthalmology",
    "ENT (Otolaryngology)",
    "Urology",
    "Nephrology",
    "Pulmonology",
    "Rheumatology",
    "Infectious Disease",
    "Pathology",
    "General Surgery",
    "Plastic Surgery",
    "Rehabilitation Medicine",
    "Physiotherapy",
    "Nutrition",
]

SERVICE_COSTS = {
    "General Consultation": 120,
    "X-Ray Scan": 220,
    "Lab Test": 175,
    "Physiotherapy": 150,
    "Emergency Care": 320,
    "Specialist Consultation": 280,
    "Surgery Fee": 1500,
    "Maternity Care": 760,
    "Vaccination": 95,
    "Health Screening": 420,
    "Dental Checkup": 210,
    "Pharmacy Supply": 85,
    "Nutrition Counseling": 160,
    "Therapy Session": 180,
}

SERVICE_STATUSES = ["PAID", "PENDING", "PARTIAL"]


def get_db_connection():
    db = getattr(g, "db", None)
    if db is None:
        db = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        g.db = db
    return db


def init_db():
    db = sqlite3.connect(app.config["DATABASE"])
    cursor = db.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            address TEXT,
            condition TEXT,
            emergency INTEGER DEFAULT 0,
            admitted_at TEXT,
            discharged INTEGER DEFAULT 0
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            active INTEGER DEFAULT 1
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER,
            doctor TEXT,
            department TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id)
        )
        """
    )
    existing_columns = [row[1] for row in cursor.execute("PRAGMA table_info(appointments)").fetchall()]
    if "doctor_id" not in existing_columns:
        cursor.execute("ALTER TABLE appointments ADD COLUMN doctor_id INTEGER DEFAULT NULL")
    if "doctor" not in existing_columns:
        cursor.execute("ALTER TABLE appointments ADD COLUMN doctor TEXT DEFAULT NULL")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            service TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TEXT NOT NULL,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
        """
    )
    existing_columns = [row[1] for row in cursor.execute("PRAGMA table_info(bills)").fetchall()]
    if "status" not in existing_columns:
        cursor.execute("ALTER TABLE bills ADD COLUMN status TEXT NOT NULL DEFAULT 'PENDING'")
    db.commit()
    db.close()


@app.teardown_appcontext
def close_db(exception=None):
    db = getattr(g, "db", None)
    if db is not None:
        db.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


@app.context_processor
def inject_user():
    return {
        "logged_in": bool(session.get("user")),
        "current_user": session.get("user"),
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user"):
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        if VALID_LOGINS.get(username) == password:
            session["user"] = username
            flash("Welcome back, Esther. You are now signed in.", "success")
            return redirect(url_for("index"))

        flash("Invalid credentials. Please try one of the listed login combinations.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    db = get_db_connection()
    active_patients = db.execute("SELECT COUNT(*) FROM patients WHERE discharged = 0").fetchone()[0]
    emergency_cases = db.execute("SELECT COUNT(*) FROM patients WHERE discharged = 0 AND emergency = 1").fetchone()[0]
    upcoming_appointments = db.execute(
        "SELECT COUNT(*) FROM appointments WHERE appointment_time >= ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M"),),
    ).fetchone()[0]
    doctor_count = db.execute("SELECT COUNT(*) FROM doctors WHERE active = 1").fetchone()[0]
    recent_patients = db.execute(
        "SELECT first_name, last_name, admitted_at, emergency FROM patients WHERE discharged = 0 ORDER BY admitted_at DESC LIMIT 4"
    ).fetchall()
    return render_template(
        "index.html",
        stats={
            "active_patients": active_patients,
            "emergency_cases": emergency_cases,
            "upcoming_appointments": upcoming_appointments,
            "doctor_count": doctor_count,
            "recent_patients": recent_patients,
        },
    )


@app.route("/patients", methods=["GET", "POST"])
@login_required
def patients():
    db = get_db_connection()
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        age = request.form.get("age")
        gender = request.form.get("gender")
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        condition = request.form.get("condition", "").strip()
        emergency = 1 if request.form.get("emergency") == "on" else 0
        admitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not first_name or not last_name or not age or not gender or not phone:
            flash("Please complete all required patient fields.", "danger")
        else:
            db.execute(
                "INSERT INTO patients (first_name, last_name, age, gender, phone, email, address, condition, emergency, admitted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (first_name, last_name, age, gender, phone, email, address, condition, emergency, admitted_at),
            )
            db.commit()
            flash("Patient registered successfully.", "success")
            return redirect(url_for("patients"))

    query = request.args.get("q", "").strip()
    if query:
        search_query = f"%{query}%"
        patients = db.execute(
            "SELECT * FROM patients WHERE discharged = 0 AND (first_name LIKE ? OR last_name LIKE ? OR phone LIKE ?) ORDER BY emergency DESC, admitted_at DESC",
            (search_query, search_query, search_query),
        ).fetchall()
    else:
        patients = db.execute("SELECT * FROM patients WHERE discharged = 0 ORDER BY emergency DESC, admitted_at DESC").fetchall()

    emergency_queue = db.execute("SELECT * FROM patients WHERE emergency = 1 AND discharged = 0 ORDER BY admitted_at ASC").fetchall()
    return render_template("patients.html", patients=patients, emergency_queue=emergency_queue, search_query=query)


@app.route("/doctors", methods=["GET", "POST"])
@login_required
def doctors():
    db = get_db_connection()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        specialization = request.form.get("specialization", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        active = 1 if request.form.get("active") == "on" else 0

        if not name or not specialization:
            flash("Please provide the doctor's name and specialization.", "danger")
        else:
            db.execute(
                "INSERT INTO doctors (name, specialization, phone, email, active) VALUES (?, ?, ?, ?, ?)",
                (name, specialization, phone, email, active),
            )
            db.commit()
            flash("Doctor profile added successfully.", "success")
            return redirect(url_for("doctors"))

    doctors = db.execute("SELECT * FROM doctors ORDER BY active DESC, name ASC").fetchall()
    return render_template("doctors.html", doctors=doctors, departments=DEPARTMENTS)


@app.route("/appointments", methods=["GET", "POST"])
@login_required
def appointments():
    db = get_db_connection()
    patients = db.execute("SELECT id, first_name, last_name FROM patients WHERE discharged = 0").fetchall()
    doctors = db.execute("SELECT id, name, specialization FROM doctors WHERE active = 1 ORDER BY name ASC").fetchall()

    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        doctor_id = request.form.get("doctor_id")
        department = request.form.get("department", "").strip()
        appointment_time = request.form.get("appointment_time", "").strip().replace("T", " ")
        notes = request.form.get("notes", "").strip()

        if not patient_id or not doctor_id or not department or not appointment_time:
            flash("Please fill in all appointment details.", "danger")
        else:
            db.execute(
                "INSERT INTO appointments (patient_id, doctor_id, department, appointment_time, notes) VALUES (?, ?, ?, ?, ?)",
                (patient_id, doctor_id, department, appointment_time, notes),
            )
            db.commit()
            flash("Appointment scheduled successfully.", "success")
            return redirect(url_for("appointments"))

    scheduled = db.execute(
        "SELECT a.id, COALESCE(d.name, a.doctor) AS doctor_name, a.department, a.appointment_time, p.first_name, p.last_name FROM appointments a JOIN patients p ON a.patient_id = p.id LEFT JOIN doctors d ON a.doctor_id = d.id ORDER BY appointment_time ASC"
    ).fetchall()
    return render_template("appointment.html", patients=patients, doctors=doctors, scheduled=scheduled, departments=DEPARTMENTS)


@app.route("/report/<int:patient_id>")
@login_required
def report(patient_id):
    db = get_db_connection()
    patient = db.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if patient is None:
        flash("Patient not found.", "danger")
        return redirect(url_for("patients"))

    appointments = db.execute(
        "SELECT a.appointment_time, COALESCE(d.name, a.doctor) AS doctor_name, a.department, a.notes FROM appointments a LEFT JOIN doctors d ON a.doctor_id = d.id WHERE a.patient_id = ? ORDER BY appointment_time DESC",
        (patient_id,),
    ).fetchall()
    bills = db.execute("SELECT * FROM bills WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,)).fetchall()
    return render_template("reports.html", patient=patient, appointments=appointments, bills=bills)


@app.route("/billing", methods=["GET", "POST"])
@login_required
def billing():
    db = get_db_connection()
    patients = db.execute("SELECT id, first_name, last_name FROM patients WHERE discharged = 0").fetchall()
    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        service = request.form.get("service")
        amount = float(request.form.get("amount", 0))
        status = request.form.get("status", "PENDING").strip().upper()

        if status not in SERVICE_STATUSES:
            status = "PENDING"

        if not patient_id or not service or amount <= 0:
            flash("Please select a patient and a valid service.", "danger")
        else:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.execute(
                "INSERT INTO bills (patient_id, service, amount, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (patient_id, service, amount, status, created_at),
            )
            db.commit()
            flash("Billing entry added successfully.", "success")
            return redirect(url_for("billing"))

    bills = db.execute(
        "SELECT b.id, b.service, b.amount, b.status, b.created_at, p.first_name, p.last_name FROM bills b JOIN patients p ON b.patient_id = p.id ORDER BY b.created_at DESC"
    ).fetchall()
    return render_template("billing.html", patients=patients, bills=bills, service_costs=SERVICE_COSTS, service_statuses=SERVICE_STATUSES)


@app.route("/update-bill-status/<int:bill_id>/<status>")
@login_required
def update_bill_status(bill_id, status):
    if status not in SERVICE_STATUSES:
        status = "PENDING"
    db = get_db_connection()
    db.execute("UPDATE bills SET status = ? WHERE id = ?", (status, bill_id))
    db.commit()
    flash(f"Bill status updated to {status}.", "success")
    return redirect(url_for("billing"))


@app.route("/receipt/<int:bill_id>")
@login_required
def receipt(bill_id):
    db = get_db_connection()
    bill = db.execute(
        "SELECT b.*, p.first_name, p.last_name, p.phone, p.email, p.address FROM bills b JOIN patients p ON b.patient_id = p.id WHERE b.id = ?",
        (bill_id,),
    ).fetchone()
    if bill is None:
        flash("Receipt not found.", "danger")
        return redirect(url_for("billing"))

    return render_template("receipt.html", bill=bill)


@app.route("/discharge/<int:patient_id>")
@login_required
def discharge(patient_id):
    db = get_db_connection()
    db.execute("UPDATE patients SET discharged = 1 WHERE id = ?", (patient_id,))
    db.commit()
    flash("Patient discharged and archived.", "success")
    return redirect(url_for("patients"))


@app.route("/archive")
@login_required
def archive():
    db = get_db_connection()
    discharged = db.execute("SELECT * FROM patients WHERE discharged = 1 ORDER BY admitted_at DESC").fetchall()
    return render_template("discharge.html", discharged=discharged)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5002)
