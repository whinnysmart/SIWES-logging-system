import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

#Initialize Flask app
app = Flask(__name__)
app.secret_key = "whinnysmart123"

#Connect to DB
def get_db_connection():
    conn = sqlite3.connect('instance/siwes.db')
    conn.row_factory = sqlite3.Row
    return conn

#Home page route
@app.route("/")
def home():
    return render_template("home.html")

#Log route
@app.route("/log", methods=["GET", "POST"])
def log():
    if request.method == "POST":
        date = request.form["date"]
        activity = request.form["activity"]

        conn = get_db_connection()
        conn.execute("INSERT INTO logs (date, activity) VALUES (?, ?)", (date, activity))
        conn.commit()
        conn.close()

        flash("Log submitted successfully!", "success")
        return redirect(url_for("log"))

    return render_template("log.html")

#Supervisor route
@app.route("/supervisor")
def supervisor():
    conn = get_db_connection()
    logs = conn.execute("SELECT * FROM logs").fetchall()
    conn.close()
    return render_template("supervisor.html", logs=logs)

#Update status route
@app.route("/update_status/<int:log_id>", methods=["POST"])
def update_status(log_id):
    action = request.form["action"]
    new_status = "Approved" if action == "approve" else "Disapproved"

    conn = get_db_connection()
    conn.execute("UPDATE logs SET status = ? WHERE id = ?", (new_status, log_id))
    conn.commit()
    conn.close()

    flash(f"Log {log_id} marked as {new_status}!", "info")
    return redirect(url_for("supervisor"))

#Feedback route
@app.route("/add_feedback/<int:log_id>", methods=["POST"])
def add_feedback(log_id):
    feedback = request.form.get("feedback")

    conn = get_db_connection()
    conn.execute("UPDATE logs SET feedback = ? WHERE id = ?", (feedback, log_id))
    conn.commit()
    conn.close()

    flash(f"Feedback added for Log {log_id}", "info")
    return redirect(url_for("supervisor"))

#Student Logs route
@app.route("/student")
def student():
    conn = get_db_connection()
    logs = conn.execute("SELECT * FROM logs").fetchall()
    conn.close()
    return render_template("student.html", logs=logs)

#Edit log route
@app.route("/edit_log/<int:log_id>", methods=["GET", "POST"])
def edit_log(log_id):
    conn = get_db_connection()
    log = conn.execute("SELECT * FROM logs WHERE id = ?", (log_id,)).fetchone()

    if request.method == "POST":
        new_date = request.form["date"]
        new_activity = request.form["activity"]

        conn.execute("UPDATE logs SET date = ?, activity = ? WHERE id = ?", (new_date, new_activity, log_id))
        conn.commit()
        conn.close()

        flash(f"Log {log_id} updated successfully!", "success")
        return redirect(url_for("student"))

    conn.close()
    return render_template("edit_log.html", log=log)

#Delete log route
@app.route("/delete_log/<int:log_id>", methods=["POST"])
def delete_log(log_id):
    # conn = get_db_connection()
    # conn.execute("DELETE FROM logs WHERE id = ?", (log_id,))
    # conn.commit()
    # conn.close()

    # flash(f"Log {log_id} deleted successfully!", "warning")
    # return redirect(url_for("supervisor"))
    pass

#Error handling route
if __name__ == "__main__":
    app.run(debug=True)