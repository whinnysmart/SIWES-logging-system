from flask import Flask, render_template, request, redirect, url_for, flash

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

        print(f"Date: {date}, Activity: {activity}")

        flash("Log submitted successfully!", "success")
        return redirect(url_for("log"))

    return render_template("log.html")

#Supervisor route
@app.route("/supervisor")
def supervisor():
    return render_template("supervisor.html")

if __name__ == "__main__":
    app.run(debug=True)