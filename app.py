import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import timedelta

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "whinnysmart123"

# Session timeout
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

# Initialize Flask extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Assign DB path
Database = "instance/siwes.db"

# User model
class User(UserMixin):
    def __init__(self, id, username, password_hash, role):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role

# Load user function
@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(Database)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    user = cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
    conn.close()

    if user:
        return User(user["id"], user["username"], user["password_hash"], user["role"])
    return None

# DB connection helper
def get_db_connection():
    conn = sqlite3.connect(Database)
    conn.row_factory = sqlite3.Row
    return conn

# Home page
@app.route("/")
def home():
    return render_template("home.html")

# Register route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
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

    return render_template("register.html")

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
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

            if user["role"] == "student":
                return redirect(url_for("student"))
            elif user["role"] == "supervisor":
                return redirect(url_for("supervisor"))
            elif user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                flash("Invalid role!", "danger")
                return redirect(url_for("login"))
        else:
            flash("Invalid username or password!", "danger")

    return render_template("login.html")

# Admin login (alternative form)
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND role = 'admin'", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user["password_hash"], password):
            user_obj = User(user["id"], user["username"], user["password_hash"], user["role"])
            login_user(user_obj)
            session.permanent = True
            flash("Admin login successful!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin credentials!", "danger")

    return render_template("admin_login.html")

# Logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))

# Student dashboard
@app.route("/student")
@login_required
def student():
    if current_user.role != "student":
        flash("Access Denied! Students only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs WHERE student_id = ? ORDER BY date DESC", (current_user.id,))
    logs = cursor.fetchall()
    conn.close()

    return render_template("student.html", logs=logs)

# Supervisor dashboard
@app.route("/supervisor")
@login_required
def supervisor():
    if current_user.role != "supervisor":
        flash("Access Denied! Supervisors only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT logs.*, users.username
        FROM logs
        JOIN users ON logs.student_id = users.id
        WHERE users.supervisor_id = ?
        ORDER BY logs.date DESC
        """,
        (current_user.id,),
    )
    logs = cursor.fetchall()
    conn.close()

    return render_template("supervisor.html", logs=logs)

# Admin dashboard
@app.route("/admin_dashboard")
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        flash("Access Denied! Admins only.", "danger")
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html")

# View and assign students to supervisors
@app.route("/assign_students", methods=["GET", "POST"])
@login_required
def assign_students():
    if current_user.role != "admin":
        flash("Access Denied! Admins only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        student_id = request.form.get("student_id")
        supervisor_id = request.form.get("supervisor_id")

        cursor.execute(
            "UPDATE users SET supervisor_id = ? WHERE id = ?",
            (supervisor_id, student_id)
        )
        conn.commit()
        flash("Student assigned successfully!", "success")
        return redirect(url_for("assign_students"))

    # Fetch students with their supervisor's name (if assigned)
    cursor.execute("""
        SELECT s.id as student_id, s.username as student_username, 
               s.supervisor_id, u.username as supervisor_username
        FROM users s
        LEFT JOIN users u ON s.supervisor_id = u.id
        WHERE s.role = 'student'
    """)
    students = cursor.fetchall()

    # Fetch all supervisors for dropdown
    cursor.execute("SELECT id, username FROM users WHERE role = 'supervisor'")
    supervisors = cursor.fetchall()

    conn.close()

    return render_template("assign_students.html", students=students, supervisors=supervisors)

# Student log submission
@app.route("/log", methods=["GET", "POST"])
@login_required
def log():
    if current_user.role != "student":
        flash("Only students can log activities.", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        date = request.form["date"]
        activity = request.form["activity"]

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO logs (date, activity, status, feedback, student_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date, activity, "pending", "", current_user.id),
        )
        conn.commit()
        conn.close()

        flash("Log submitted successfully!", "success")
        return redirect(url_for("student"))

    return render_template("log.html")

# Edit log
@app.route("/edit_log/<int:log_id>", methods=["GET", "POST"])
@login_required
def edit_log(log_id):
    if current_user.role != "student":
        flash("Access Denied! Students only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    log = conn.execute("SELECT * FROM logs WHERE id = ?", (log_id,)).fetchone()

    if request.method == "POST":
        new_date = request.form["date"]
        new_activity = request.form["activity"]

        conn.execute(
            "UPDATE logs SET date = ?, activity = ?, status = 'pending', feedback = NULL WHERE id = ?",
            (new_date, new_activity, log_id),
        )
        conn.commit()
        conn.close()

        flash(f"Log {log_id} updated successfully!", "success")
        return redirect(url_for("student"))

    conn.close()
    return render_template("edit_log.html", log=log)

# Delete log
@app.route("/delete_log/<int:log_id>")
@login_required
def delete_log(log_id):
    if current_user.role != "student":
        flash("Access Denied! Students only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    conn.execute("DELETE FROM logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()

    flash(f"Log {log_id} deleted successfully!", "warning")
    return redirect(url_for("student"))

# Supervisor updates status
@app.route("/update_status/<int:log_id>", methods=["POST"])
@login_required
def update_status(log_id):
    if current_user.role != "supervisor":
        flash("Access Denied! Supervisor only.", "danger")
        return redirect(url_for("login"))

    action = request.form["action"]
    new_status = "Approved" if action == "approve" else "Disapproved"

    conn = get_db_connection()
    conn.execute("UPDATE logs SET status = ? WHERE id = ?", (new_status, log_id))
    conn.commit()
    conn.close()

    flash(f"Log {log_id} marked as {new_status}!", "info")
    return redirect(url_for("supervisor"))

# Supervisor adds feedback
@app.route("/add_feedback/<int:log_id>", methods=["POST"])
@login_required
def add_feedback(log_id):
    if current_user.role != "supervisor":
        flash("Access Denied! Supervisor only.", "danger")
        return redirect(url_for("login"))

    feedback = request.form.get("feedback")

    conn = get_db_connection()
    conn.execute("UPDATE logs SET feedback = ? WHERE id = ?", (feedback, log_id))
    conn.commit()
    conn.close()

    flash(f"Feedback added for Log {log_id}", "info")
    return redirect(url_for("supervisor"))

# Run app
if __name__ == "__main__":
    app.run(debug=True)
