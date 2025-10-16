import os
from flask import Blueprint, render_template, redirect, url_for, flash, send_file, current_app, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_bcrypt import generate_password_hash, check_password_hash
import sqlite3

from db_utils import get_db_connection


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def get_db_connection():
    db_path = current_app.config.get('DATABASE', 'instance/siwes.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# ------------------------
# ADMIN DASHBOARD
# ------------------------
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    # only admins allowed
    if current_user.role != 'admin':
        flash("Access Denied! Admins only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()

    # counts
    total_students = cur.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0]
    total_supervisors = cur.execute("SELECT COUNT(*) FROM users WHERE role = 'supervisor'").fetchone()[0]
    total_logs = cur.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
    pending_logs = cur.execute("SELECT COUNT(*) FROM logs WHERE lower(status) = 'pending'").fetchone()[0]
    approved_logs = cur.execute("SELECT COUNT(*) FROM logs WHERE lower(status) = 'approved'").fetchone()[0]

    # recent activities - latest 6 logs
    activities = cur.execute("""
        SELECT logs.id, users.username AS student, logs.date, logs.status
        FROM logs
        JOIN users ON logs.student_id = users.id
        ORDER BY datetime(logs.date) DESC
        LIMIT 6
    """).fetchall()

    conn.close()

    stats = {
        "total_students": total_students,
        "total_supervisors": total_supervisors,
        "total_logs": total_logs,
        "pending_logs": pending_logs,
        "approved_logs": approved_logs
    }

    return render_template('admin/dashboard.html', stats=stats, activities=activities)

# ------------------------
# MANAGE STUDENTS
# ------------------------
@admin_bp.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    """Admin view + manage all students (assign, delete)."""
    if current_user.role != 'admin':
        flash("Access Denied! Admins only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()

    # If admin submitted an assignment form
    if request.method == "POST":
        action = request.form.get("action")

        if action == "assign":
            student_id = request.form.get("student_id")
            supervisor_id = request.form.get("supervisor_id")
            cur.execute("UPDATE users SET supervisor_id = ? WHERE id = ?", (supervisor_id, student_id))
            conn.commit()
            flash("Supervisor assigned successfully!", "success")

        elif action == "delete":
            student_id = request.form.get("student_id")
            cur.execute("DELETE FROM users WHERE id = ? AND role = 'student'", (student_id,))
            cur.execute("DELETE FROM logs WHERE student_id = ?", (student_id,))
            conn.commit()
            flash("Student record deleted!", "danger")

        return redirect(url_for('admin.students'))

    # Search and pagination
    q = request.args.get('q', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page

    if q:
        students = cur.execute("""
            SELECT s.id, s.username AS student_name, u.username AS supervisor_name
            FROM users s
            LEFT JOIN users u ON s.supervisor_id = u.id
            WHERE s.role='student' AND s.username LIKE ?
            ORDER BY s.username LIMIT ? OFFSET ?;
        """, (f'%{q}%', per_page, offset)).fetchall()

        total = cur.execute("SELECT COUNT(*) FROM users WHERE role='student' AND username LIKE ?", (f'%{q}%',)).fetchone()[0]
    else:
        students = cur.execute("""
            SELECT s.id, s.username AS student_name, u.username AS supervisor_name
            FROM users s
            LEFT JOIN users u ON s.supervisor_id = u.id
            WHERE s.role='student'
            ORDER BY s.username LIMIT ? OFFSET ?;
        """, (per_page, offset)).fetchall()

        total = cur.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]

    # Get all supervisors for dropdown
    supervisors = cur.execute("SELECT id, username FROM users WHERE role='supervisor' ORDER BY username;").fetchall()

    conn.close()
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'admin/students.html',
        students=students,
        supervisors=supervisors,
        q=q,
        page=page,
        total_pages=total_pages
    )

# ------------------------
# MANAGE SUPERVISORS
# ------------------------
@admin_bp.route('/supervisors', methods=['GET', 'POST'])
@login_required
def supervisors():
    """Admin view + manage all supervisors."""
    if current_user.role != 'admin':
        flash("Access Denied! Admins only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()

    # ADD NEW SUPERVISOR
    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            username = request.form.get("username").strip()
            password = request.form.get("password").strip()
            if not username or not password:
                flash("Both username and password are required.", "warning")
            else:
                from flask_bcrypt import generate_password_hash
                password_hash = generate_password_hash(password).decode("utf-8")
                try:
                    cur.execute(
                        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'supervisor')",
                        (username, password_hash)
                    )
                    conn.commit()
                    flash(f"Supervisor '{username}' added successfully!", "success")
                except Exception as e:
                    flash("Error: Supervisor username already exists!", "danger")

        elif action == "delete":
            supervisor_id = request.form.get("supervisor_id")
            # Unassign all students under this supervisor
            cur.execute("UPDATE users SET supervisor_id = NULL WHERE supervisor_id = ?", (supervisor_id,))
            # Delete supervisor
            cur.execute("DELETE FROM users WHERE id = ? AND role='supervisor'", (supervisor_id,))
            conn.commit()
            flash("Supervisor deleted and students unassigned.", "danger")

        return redirect(url_for('admin.supervisors'))

    # FETCH SUPERVISORS AND STUDENT COUNT
    supervisors = cur.execute("""
        SELECT u.id, u.username, COUNT(s.id) AS total_students
        FROM users u
        LEFT JOIN users s ON u.id = s.supervisor_id AND s.role='student'
        WHERE u.role='supervisor'
        GROUP BY u.id
        ORDER BY u.username;
    """).fetchall()

    conn.close()
    return render_template('admin/supervisors.html', supervisors=supervisors)

# ------------------------
# LOGS VIEW (filterable)
# ------------------------
@admin_bp.route('/logs')
@login_required
def logs():
    if current_user.role != 'admin':
        flash("Access Denied! Admins only.", "danger")
        return redirect(url_for("login"))

    status = request.args.get('status', 'all')  # 'all', 'pending', 'approved', 'disapproved'
    page = int(request.args.get('page', 1))
    per_page = 25
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cur = conn.cursor()

    base_q = """
        SELECT logs.id, logs.date, logs.activity, logs.status, users.username AS student
        FROM logs JOIN users ON logs.student_id = users.id
    """
    params = []
    if status and status != 'all':
        base_q += " WHERE lower(logs.status) = ? "
        params.append(status.lower())

    base_q += " ORDER BY datetime(logs.date) DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])

    rows = cur.execute(base_q, tuple(params)).fetchall()

    # total count for pagination
    count_q = "SELECT COUNT(*) FROM logs"
    if status and status != 'all':
        count_q += " WHERE lower(status) = ?"
        total = cur.execute(count_q, (status.lower(),)).fetchone()[0]
    else:
        total = cur.execute(count_q).fetchone()[0]

    conn.close()

    total_pages = (total + per_page - 1) // per_page
    return render_template('admin/logs.html', logs=rows, status=status, page=page, total_pages=total_pages)

# ------------------------
# BULK ACTION ON LOGS
# ------------------------
@admin_bp.route('/logs/action', methods=['POST'])
@login_required
def logs_action():
    """Admin performs bulk actions (approve, disapprove, delete)."""
    if current_user.role != 'admin':
        flash("Access Denied! Admins only.", "danger")
        return redirect(url_for("login"))

    action = request.form.get('action')
    selected_logs = request.form.getlist('selected_logs')

    if not selected_logs:
        flash("No logs selected.", "warning")
        return redirect(url_for('admin.logs'))

    conn = get_db_connection()
    cur = conn.cursor()

    if action == "approve":
        cur.executemany("UPDATE logs SET status = 'approved' WHERE id = ?", [(lid,) for lid in selected_logs])
        flash(f"{len(selected_logs)} log(s) approved!", "success")

    elif action == "disapprove":
        cur.executemany("UPDATE logs SET status = 'disapproved' WHERE id = ?", [(lid,) for lid in selected_logs])
        flash(f"{len(selected_logs)} log(s) disapproved!", "warning")

    elif action == "delete":
        cur.executemany("DELETE FROM logs WHERE id = ?", [(lid,) for lid in selected_logs])
        flash(f"{len(selected_logs)} log(s) deleted!", "danger")

    else:
        flash("Invalid action.", "danger")

    conn.commit()
    conn.close()

    return redirect(url_for('admin.logs'))

# --------------------------
# ADMIN SETTINGS PAGE
# --------------------------
@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Admin settings: password change, DB backup, and system info."""
    if current_user.role != 'admin':
        flash("Access Denied! Admins only.", "danger")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()

    # Get quick system stats
    total_students = cur.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
    total_supervisors = cur.execute("SELECT COUNT(*) FROM users WHERE role='supervisor'").fetchone()[0]
    total_logs = cur.execute("SELECT COUNT(*) FROM logs").fetchone()[0]

    conn.close()

    # Handle password change
    if request.method == "POST":
        if request.form.get("action") == "change_password":
            old_password = request.form.get("old_password")
            new_password = request.form.get("new_password")
            confirm_password = request.form.get("confirm_password")

            conn = get_db_connection()
            admin_user = conn.execute("SELECT * FROM users WHERE id = ?", (current_user.id,)).fetchone()
            conn.close()

            if not check_password_hash(admin_user["password_hash"], old_password):
                flash("Old password is incorrect!", "danger")
            elif new_password != confirm_password:
                flash("New passwords do not match!", "warning")
            else:
                hashed = generate_password_hash(new_password).decode("utf-8")
                conn = get_db_connection()
                conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, current_user.id))
                conn.commit()
                conn.close()
                flash("Password changed successfully!", "success")
                return redirect(url_for('admin.settings'))

        elif request.form.get("action") == "backup":
            # Generate a database backup copy
            backup_filename = f"siwes_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            db_path = os.path.join("instance", "siwes.db")
            backup_path = os.path.join("backups", backup_filename)
            os.makedirs("backups", exist_ok=True)
            with open(db_path, "rb") as src, open(backup_path, "wb") as dst:
                dst.write(src.read())
            flash("Database backup created successfully!", "success")
            return send_file(backup_path, as_attachment=True)

    # Get DB size for display
    db_size = os.path.getsize("instance/siwes.db") / 1024  # in KB

    return render_template(
        'admin/settings.html',
        total_students=total_students,
        total_supervisors=total_supervisors,
        total_logs=total_logs,
        db_size=round(db_size, 2)
    )