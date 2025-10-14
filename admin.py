from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    # Fetch summary data
    stats = {
        "total_students": 120,
        "total_supervisors": 12,
        "pending_logs": 35,
        "approved_logs": 480
    }
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/students')
@login_required
def students():
    # Fetch students from database
    return render_template('admin/students.html')

@admin_bp.route('/supervisors')
@login_required
def supervisors():
    return render_template('admin/supervisors.html')

@admin_bp.route('/logs')
@login_required
def logs():
    return render_template('admin/logs.html')

@admin_bp.route('/settings')
@login_required
def settings():
    return render_template('admin/settings.html')