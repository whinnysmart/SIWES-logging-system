from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/log")
def log():
    return render_template("log.html")

@app.route("/supervisor")
def supervisor():
    return render_template("supervisor.html")

if __name__ == "__main__":
    app.run(debug=True)