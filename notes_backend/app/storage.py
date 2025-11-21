from flask import current_app
from .models import StorageService


# PUBLIC_INTERFACE
def get_storage() -> StorageService:
    """
    Return the initialized StorageService from the Flask app context.

    The StorageService is attached to app.extensions["storage_service"] during app creation.
    If not present (e.g., during tests without app factory), a default instance will be created.
    """
    svc = current_app.extensions.get("storage_service")  # type: ignore[assignment]
    if not isinstance(svc, StorageService):
        # Fallback in case app factory didn't set it (e.g., tests)
        svc = StorageService()
        current_app.extensions["storage_service"] = svc
    return svc
