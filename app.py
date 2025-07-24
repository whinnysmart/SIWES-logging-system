import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

def get_db_connection():
    conn = sqlite3.connect('instance/siwes.db')
    conn.row_factory = sqlite3.Row
    return conn

app = Flask(__name__)
app.secret_key = "whinnysmart123"

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
    new_status = "approved" if action == "approve" else "disapproved"

    conn = get_db_connection()
    conn.execute("UPDATE logs SET status = ? WHERE id = ?", (new_status, log_id))
    conn.commit()
    conn.close()

    flash(f"Log {log_id} marked as {new_status}!", "info")
    return redirect(url_for("supervisor"))

if __name__ == "__main__":
    app.run(debug=True)