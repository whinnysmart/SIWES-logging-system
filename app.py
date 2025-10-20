import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import timedelta
from admin import admin_bp

from db_utils import get_db_connection

# --------------------------
# FLASK APP CONFIG
# --------------------------
app = Flask(__name__)
app.secret_key = "whinnysmart123"

# SQLite DB path
Database = "instance/siwes.db"

# Session settings
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=10)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
app.config['DATABASE'] = Database

# Flask extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# --------------------------
# REGISTER BLUEPRINTS
# --------------------------
app.register_blueprint(admin_bp)


# --------------------------
# USER MODEL
# --------------------------
class User(UserMixin):
    def __init__(self, id, username, password_hash, role):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role


# --------------------------
# LOGIN MANAGER LOADER
# --------------------------
@login_manager.user_loader
def load_user(user_id):
    """Load user object from DB using user_id (needed for Flask-Login)."""
    conn = sqlite3.connect(Database)
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
    conn.close()

    if user:
        return User(user["id"], user["username"], user["password_hash"], user["role"])
    return None


# --------------------------
# ROUTES
# --------------------------

@app.route("/")
def home():
    return render_template("home.html", Page ='home')


# --------------------------
# REGISTER
# --------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    """Allow new students/supervisors."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role),
            )
            conn.commit()

            flash("User registered successfully! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists!", "danger")
        finally:
            conn.close()

    return render_template("register.html", Page ='register')


# --------------------------
# LOGIN
# --------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """Single login route for all roles."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user["password_hash"], password):
            user_obj = User(user["id"], user["username"], user["password_hash"], user["role"])
            login_user(user_obj)
            session.permanent = True
            flash("Login successful!", "success")

            # Redirect based on role
            if user["role"] == "student":
                return redirect(url_for("student"))
            elif user["role"] == "supervisor":
                return redirect(url_for("supervisor"))
            elif user["role"] == "admin":
                return redirect(url_for("admin.dashboard"))
            else:
                flash("Invalid role!", "danger")
                return redirect(url_for("login"))
        else:
            flash("Invalid username or password!", "danger")

    return render_template("login.html", Page ='login')


# --------------------------
# LOGOUT
# --------------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))


# --------------------------
# STUDENT DASHBOARD
# --------------------------
@app.route("/student")
@login_required
def student():
    """Student dashboard showing their own logs."""
    if current_user.role != "student":
        flash("Access Denied! Students only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()

    # Fetch all logs for this student
    logs = conn.execute(
        "SELECT * FROM logs WHERE student_id = ? ORDER BY date DESC", 
        (current_user.id,)
    ).fetchall()

    # Stats
    total_logs = len(logs)
    pending_logs = len([log for log in logs if log["status"].lower() == "pending"])
    approved_logs = len([log for log in logs if log["status"].lower() == "approved"])

    # Recent 5 logs for table display
    recent_logs = logs[:5]

    conn.close()

    return render_template(
        "student.html",
        total_logs=total_logs,
        pending_logs=pending_logs,
        approved_logs=approved_logs,
        recent_logs=recent_logs, 
        Page ='student'
    )

# --------------------------
# STUDENT LOG SUBMISSION
# --------------------------
@app.route("/log", methods=["GET", "POST"])
@login_required
def log():
    """Students submit logs for their activities."""
    if current_user.role != "student":
        flash("Only students can log activities.", "danger")
        return redirect(url_for("student"))

    if request.method == "POST":
        date = request.form["date"]
        activity = request.form["activity"]

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO logs (date, activity, status, feedback, student_id) VALUES (?, ?, ?, ?, ?)",
            (date, activity, "pending", "", current_user.id),
        )
        conn.commit()
        conn.close()

        flash("Log submitted successfully!", "success")
        return redirect(url_for("student"))

    return render_template("log.html", Page ='log')


# --------------------------
# STUDENT EDIT LOG
# --------------------------
@app.route("/edit_log/<int:log_id>", methods=["GET", "POST"])
@login_required
def edit_log(log_id):
    """Students can edit their previous logs."""
    if current_user.role != "student":
        flash("Access Denied! Students only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    log = conn.execute("SELECT * FROM logs WHERE id = ? AND student_id = ?", (log_id, current_user.id)).fetchone()

    if not log:
        conn.close()
        flash("Log not found or access denied.", "danger")
        return redirect(url_for("student"))

    if request.method == "POST":
        new_date = request.form["date"]
        new_activity = request.form["activity"]

        conn.execute(
            "UPDATE logs SET date = ?, activity = ?, status = 'pending', feedback = NULL WHERE id = ?",
            (new_date, new_activity, log_id),
        )
        conn.commit()
        conn.close()

        flash(f"Log '{new_date}' updated successfully!", "success")
        return redirect(url_for("student"))

    conn.close()
    return render_template("edit_log.html", log=log, Page ='edit_log')


# --------------------------
# STUDENT DELETE LOG
# --------------------------
@app.route("/delete_log/<int:log_id>", methods=["POST", "GET"])
@login_required
def delete_log(log_id):
    """Students delete their own logs."""
    if current_user.role != "student":
        flash("Access Denied! Students only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    # ensure student owns the log before deleting
    conn.execute("DELETE FROM logs WHERE id = ? AND student_id = ?", (log_id, current_user.id))
    conn.commit()
    conn.close()

    flash(f"Log {log_id} deleted successfully!", "warning")
    return redirect(url_for("student"))


# --------------------------
# SUPERVISOR DASHBOARD (FILTERS + FEEDBACK + ACTIONS)
# --------------------------
@app.route("/supervisor", methods=["GET", "POST"])
@login_required
def supervisor():
    """Supervisors view logs of their assigned students, with filters and actions."""
    if current_user.role != 'supervisor':
        flash("Access Denied! Supervisors only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()

    # Fetch only students assigned to this supervisor
    students = conn.execute("SELECT id, username FROM users WHERE role = 'student' AND supervisor_id = ?", (current_user.id,)).fetchall()

    selected_student = "all"
    start_date = None
    end_date = None

    query = """
        SELECT logs.*, users.username
        FROM logs
        JOIN users ON logs.student_id = users.id
        WHERE users.supervisor_id = ?
    """
    params = [current_user.id]

    if request.method == "POST":
        # Reset button clears filters
        if "reset" in request.form:
            conn.close()
            return redirect(url_for("supervisor"))

        selected_student = request.form.get("student_id", "all")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")

        if selected_student != "all":
            query += " AND users.id = ?"
            params.append(selected_student)

        if start_date:
            query += " AND logs.date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND logs.date <= ?"
            params.append(end_date)

    query += " ORDER BY logs.date DESC"
    logs = conn.execute(query, tuple(params)).fetchall()

    conn.close()

    return render_template(
        "supervisor.html",
        logs=logs,
        students=students,
        selected_student=selected_student,
        start_date=start_date,
        end_date=end_date, 
        Page ='supervisor'
    )


# --------------------------
# SUPERVISOR: UPDATE STATUS
# --------------------------
@app.route("/update_status/<int:log_id>", methods=["POST"])
@login_required
def update_status(log_id):
    """Supervisor approves or disapproves a student's log."""
    if current_user.role != "supervisor":
        flash('Access Denied! Supervisor only.', "danger")
        return redirect(url_for("login"))

    action = request.form.get("action")
    new_status = "Approved" if action == "approve" else "Disapproved"

    conn = get_db_connection()
    conn.execute("UPDATE logs SET status = ? WHERE id = ?", (new_status, log_id))
    conn.commit()
    conn.close()

    flash(f"Log {log_id} marked as {new_status}!", "info")
    return redirect(url_for("supervisor"))


# --------------------------
# SUPERVISOR: ADD FEEDBACK
# --------------------------
@app.route("/add_feedback/<int:log_id>", methods=["POST"])
@login_required
def add_feedback(log_id):
    """Supervisor adds feedback to a student's log."""
    if current_user.role != "supervisor":
        flash('Access Denied! Supervisor only.', "danger")
        return redirect(url_for("login"))

    feedback = request.form.get("feedback", "").strip()

    conn = get_db_connection()
    conn.execute("UPDATE logs SET feedback = ? WHERE id = ?", (feedback, log_id))
    conn.commit()
    conn.close()

    flash(f"Feedback added for Log {log_id}", "info")
    return redirect(url_for("supervisor"))


# --------------------------
# FILTER LOGS BY DATE (STUDENT)
# --------------------------
@app.route("/logs_by_date", methods=["GET", "POST"])
@login_required
def logs_by_date():
    """Students filter their logs by a specific date."""
    if current_user.role != "student":
        flash("Access Denied! Students only.", "danger")
        return redirect(url_for("login"))

    logs = []
    selected_date = None

    if request.method == "POST":
        selected_date = request.form.get("date")

        conn = get_db_connection()
        logs = conn.execute(
            "SELECT * FROM logs WHERE student_id = ? AND date(date) = ? ORDER BY date DESC",
            (current_user.id, selected_date),
        ).fetchall()
        conn.close()

    return render_template("logs_by_date.html", logs=logs, selected_date=selected_date, Page ='logs_by_date')


# --------------------------
# RUN APP
# --------------------------
if __name__ == "__main__":
    app.run(debug=True)
