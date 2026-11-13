import os
import logging
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from config import Config
from database import db
from routes.conversation_routes import conversation_bp
from routes.chat_routes import chat_bp
from routes.file_routes import file_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("memoraai")


def create_app(config_class=Config):
    """Application factory for MemoraAI Flask application."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_class)

    # Ensure uploads folder exists
    os.makedirs(app.config.get("UPLOAD_FOLDER", "uploads"), exist_ok=True)

    # Enable CORS for REST API endpoints
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize SQLAlchemy
    db.init_app(app)

    # Register API Blueprints
    app.register_blueprint(conversation_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(file_bp)

    # Frontend Route
    @app.route("/")
    def index():
        """Serve the primary MemoraAI Single Page Application."""
        return render_template(
            "index.html",
            app_name=Config.APP_NAME,
            tagline=Config.TAGLINE,
            version=Config.VERSION,
            model_name=app.config.get("OPENAI_MODEL", "gemini-3.5-flash-lite"),
        )

    # Global Error Handlers
    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(413)
    def handle_file_too_large(e):
        return jsonify({"error": "File size exceeds maximum allowed upload limit (25MB)."}), 413

    @app.errorhandler(500)
    def handle_internal_server_error(e):
        logger.error(f"Internal server error: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred"}), 500

    # Ensure security headers on every response
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

    # Create database tables automatically
    with app.app_context():
        db.create_all()
        logger.info("MemoraAI Database tables initialized successfully.")

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1")
    logger.info(f"Starting MemoraAI on port {port} (debug={debug})...")
    app.run(host="0.0.0.0", port=port, debug=debug)
