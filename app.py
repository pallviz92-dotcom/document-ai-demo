"""Flask backend for Document AI web app."""

import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from doc_ai_service import get_capabilities, extract_from_file

static_dir = os.path.join(os.path.dirname(__file__), "webapp", "dist")
app = Flask(__name__, static_folder=static_dir, static_url_path="")
CORS(app)


@app.route("/")
def index():
    if os.path.isdir(app.static_folder) and os.path.exists(
        os.path.join(app.static_folder, "index.html")
    ):
        return send_from_directory(app.static_folder, "index.html")
    return (
        "<p>Web app not built. Run: <code>cd webapp && npm install && npm run build</code></p>"
        "<p>Then restart this server and open <a href='/'>/</a></p>",
        200,
    )


@app.route("/login.html")
def login():
    if os.path.isdir(app.static_folder) and os.path.exists(
        os.path.join(app.static_folder, "login.html")
    ):
        return send_from_directory(app.static_folder, "login.html")
    return "Login page not found", 404


@app.route("/api/capabilities")
def api_capabilities():
    try:
        caps = get_capabilities()
        return jsonify(caps)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/extract", methods=["POST"])
def api_extract():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400
    try:
        # Get rotation from form data (0, 90, 180, 270)
        rotation = int(request.form.get("rotation", 0))
        if rotation not in (0, 90, 180, 270):
            rotation = 0
            
        result = extract_from_file(
            file.stream,
            file.filename,
            document_type=request.form.get("document_type", "invoice"),
            client_id=request.form.get("client_id", "default"),
            rotation=rotation,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
