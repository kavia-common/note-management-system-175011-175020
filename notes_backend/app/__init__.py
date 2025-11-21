from flask import Flask
from flask_cors import CORS
from flask_smorest import Api
import os
import atexit

# Local storage service
from .models import StorageService
# Blueprints
from .routes.health import blp as health_blp
from .routes.notes import blp as notes_blp


def _seed_data_if_requested(storage: StorageService) -> None:
    """
    Seed the notes table with a few sample entries when SEED_NOTES=true.
    This is a no-op if the flag is not set or falsey.
    """
    seed_flag = str(os.getenv("SEED_NOTES", "")).strip().lower()
    if seed_flag not in ("1", "true", "yes", "on"):
        return

    # Only seed if there are no notes yet
    existing, _ = storage.list_notes()
    if existing:
        return

    samples = [
        {
            "title": "Welcome to Notes",
            "content": "This is your first note. You can create, edit, search, and archive notes.",
            "tags": ["welcome", "info"],
        },
        {
            "title": "Using Tags",
            "content": "Tag notes to organize them. Try filtering by tag in the list endpoint.",
            "tags": ["tips", "tags"],
        },
        {
            "title": "Archiving",
            "content": "Archive notes you don't actively need. They remain searchable when include_archived=true.",
            "tags": ["tips", "archive"],
            "archived": False,
        },
    ]
    for s in samples:
        try:
            storage.create_note(s)
        except Exception:
            # Seeding should not break startup; ignore any individual seed errors
            pass


def create_app() -> Flask:
    """
    PUBLIC_INTERFACE
    Flask application factory.

    Responsibilities:
    - Configure CORS and OpenAPI/Swagger UI
    - Initialize and register blueprints with Api (health and notes)
    - Initialize StorageService using NOTES_DB_PATH (defaults to instance/notes.db)
    - Register teardown handlers to clean up resources
    - Optionally seed the database when SEED_NOTES=true
    """
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    CORS(app, resources={r"/*": {"origins": "*"}})

    # OpenAPI / Swagger UI settings
    app.config["API_TITLE"] = "My Flask API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/docs"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    # Initialize API and register blueprints (ensure notes blueprint is included)
    api = Api(app)
    api.register_blueprint(health_blp)
    api.register_blueprint(notes_blp)

    # Initialize storage and attach to app extensions for later use by routes
    # NOTES_DB_PATH may be provided via environment variables (managed outside code)
    db_path = os.getenv("NOTES_DB_PATH")  # StorageService will also default internally
    app.extensions = getattr(app, "extensions", {})
    storage = StorageService(db_path=db_path)
    app.extensions["storage_service"] = storage

    # Optional seeding controlled by SEED_NOTES env var
    _seed_data_if_requested(storage)

    # Teardown/cleanup: sqlite3 connections are short-lived per call, but ensure any
    # cached resources could be cleaned up here in future. We also register an atexit.
    @app.teardown_appcontext
    def _teardown(exception):  # noqa: ARG001 - flask passes exception
        # Current StorageService opens connections per operation and closes them via context managers.
        # If we later add persistent connections, close them here.
        return None

    atexit.register(lambda: None)

    return app


# For backward compatibility with run.py importing "app"
app = create_app()
