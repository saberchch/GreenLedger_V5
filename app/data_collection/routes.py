# app/data_collection/routes.py
import os
import json
from flask import Blueprint, request, jsonify

data_collection_bp = Blueprint("data_collection", __name__)

# Folder to store contact submissions
CONTACT_JSON_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "contact_submissions.json"
)

# Ensure the JSON file exists
if not os.path.exists(CONTACT_JSON_FILE):
    with open(CONTACT_JSON_FILE, "w") as f:
        json.dump([], f, indent=4)


@data_collection_bp.route("/submit_contact", methods=["POST"])
def submit_contact():
    try:
        data = {
            "full_name": request.form.get("full_name"),
            "email": request.form.get("email"),
            "organization": request.form.get("organization"),
            "job_title": request.form.get("job_title"),
            "inquiry_type": request.form.get("inquiry_type"),
            "message": request.form.get("message"),
        }

        # Validate required fields
        missing_fields = [k for k, v in data.items() if not v]
        if missing_fields:
            return jsonify({"status": "error", "message": f"Missing fields: {missing_fields}"}), 400

        # Load existing submissions
        with open(CONTACT_JSON_FILE, "r") as f:
            submissions = json.load(f)

        # Add new submission
        submissions.append(data)

        # Save back to JSON
        with open(CONTACT_JSON_FILE, "w") as f:
            json.dump(submissions, f, indent=4)

        return jsonify({"status": "success", "message": "Contact form submitted successfully!"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
