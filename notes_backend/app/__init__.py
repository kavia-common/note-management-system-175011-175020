from flask import Flask
from flask_cors import CORS
from flask_smorest import Api
import os

# Local storage service
from .models import StorageService
# Blueprints
from .routes.health import blp as health_blp
from .routes.notes import blp as notes_blp

app = Flask(__name__)
app.url_map.strict_slashes = False
CORS(app, resources={r"/*": {"origins": "*"}})
app.config["API_TITLE"] = "My Flask API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config['OPENAPI_URL_PREFIX'] = '/docs'
app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

# Initialize API
api = Api(app)
api.register_blueprint(health_blp)
api.register_blueprint(notes_blp)

# Initialize storage and attach to app extensions for later use by routes
# NOTES_DB_PATH may be provided via environment variables (managed outside code)
db_path = os.getenv("NOTES_DB_PATH")
app.extensions = getattr(app, "extensions", {})
app.extensions["storage_service"] = StorageService(db_path=db_path)
