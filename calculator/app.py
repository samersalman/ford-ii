"""FORD-II web calculator: Flask routes and result rendering."""
from flask import Flask, jsonify, render_template, request

from config import RISK_GROUPS
from prediction import score_patient

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", result=None, form={}, risk_groups=RISK_GROUPS)


@app.route("/score", methods=["POST"])
def score():
    if request.is_json:
        result = score_patient(request.get_json(silent=True) or {})
        return jsonify(result)

    form_data = request.form.to_dict(flat=True)
    result = score_patient(form_data)
    return render_template(
        "index.html",
        result=result,
        form=form_data,
        risk_groups=RISK_GROUPS,
    )


@app.route("/healthz", methods=["GET"])
def healthz():
    return {"ok": True}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
