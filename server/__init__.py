import os
import traceback
from flask import Flask, jsonify, render_template

from server.db import init_db
from server.routes.asr_routes import asr_bp
from server.routes.auth_routes import auth_bp
from server.routes.api_routes import api_bp
from server.asr import LANGUAGES, DEVICE

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "cpms-dev-secret-key-change-in-prod")
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB

    app.register_blueprint(asr_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Return JSON instead of HTML for HTTP errors and unhandled exceptions."""
        if os.environ.get("FLASK_DEBUG", "0") == "1":
            return jsonify({
                "error": "Internal Server Error",
                "message": str(e),
                "traceback": traceback.format_exc()
            }), 500
        return jsonify({"error": "Internal Server Error"}), 500

    @app.route("/")
    def index():
        return render_template(
            "index.html",
            languages=LANGUAGES,
            device=DEVICE,
        )

    with app.app_context():
        init_db()

    return app
