"""FORD-II web calculator: minimal Flask app."""
from flask import Flask, render_template, request, jsonify
from prediction import score_patient

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", result=None)

@app.route("/score", methods=["POST"])
def score():
    if request.is_json:
        result = score_patient(request.get_json(silent=True) or {})
        return jsonify(result)
    # Standard form POST -> re-render template with result
    result = score_patient(request.form)
    return render_template("index.html", result=result, form=request.form)

@app.route("/healthz", methods=["GET"])
def healthz():
    return {"ok": True}

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
