# PUBLIC_INTERFACE
"""
Routes package for the notes backend.

Exposes health and notes blueprints to allow explicit imports elsewhere:
- from app.routes import health_blueprint, notes_blueprint
"""

from .health import blp as health_blueprint  # Health check blueprint
from .notes import blp as notes_blueprint    # Notes CRUD blueprint
