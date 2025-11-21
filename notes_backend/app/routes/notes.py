from flask.views import MethodView
from flask_smorest import Blueprint, abort
from typing import Any, Dict

from ..storage import get_storage
from ..schemas import (
    NotesListQueryArgsSchema,
    NotesListResponseSchema,
    SingleNoteResponseSchema,
    NoteCreateSchema,
    NoteUpdatePutSchema,
    NoteUpdatePatchSchema,
)

blp = Blueprint(
    "Notes",
    "notes",
    url_prefix="/api/notes",
    description="CRUD operations and management for notes including filtering, pagination, and archive/restore actions.",
)


@blp.route("/")
class NotesListCreate(MethodView):
    """
    PUBLIC_INTERFACE
    Notes collection endpoints.

    GET /api/notes:
      - List notes with optional filters and pagination.
      - Supported query params: page, page_size, archived, tag, created_from, created_to, updated_from, updated_to
      - Returns list of notes with pagination metadata.

    POST /api/notes:
      - Create a new note from request body.
      - Validates with NoteCreateSchema.
      - Returns created note.
    """

    @blp.arguments(NotesListQueryArgsSchema, location="query")
    @blp.response(200, NotesListResponseSchema, description="List notes with filters and pagination", example={
        "data": [],
        "metadata": {
            "total": 0, "total_pages": 0, "first_page": 0, "last_page": 0,
            "page": 1, "previous_page": 0, "next_page": 0
        }
    })
    def get(self, args: Dict[str, Any]):
        """
        List notes with filters and pagination.
        """
        storage = get_storage()

        # Extract pagination
        page = args.get("page", 1)
        page_size = args.get("page_size", 20)

        # Build filters for storage service
        filters: Dict[str, Any] = {
            "archived": bool(args.get("archived", False)),
        }
        # Optional filters
        for key in ("tag", "created_from", "created_to", "updated_from", "updated_to"):
            if key in args and args[key] not in (None, ""):
                filters[key] = args[key]

        data, meta = storage.list_notes(filters=filters, pagination={"page": page, "page_size": page_size})
        return {"data": data, "metadata": meta}

    @blp.arguments(NoteCreateSchema)
    @blp.response(201, SingleNoteResponseSchema, description="Created note")
    def post(self, json_data: Dict[str, Any]):
        """
        Create a new note.
        """
        storage = get_storage()
        try:
            note = storage.create_note(json_data)
        except ValueError as e:
            abort(400, message=str(e))
        return {"data": note}


@blp.route("/<string:note_id>")
class NoteDetail(MethodView):
    """
    PUBLIC_INTERFACE
    Single note resource endpoints.

    GET /api/notes/{id}:
      - Retrieve a single note by ID.

    PUT /api/notes/{id}:
      - Full update of a note. All fields required.

    PATCH /api/notes/{id}:
      - Partial update of a note. Only provided fields are updated.

    DELETE /api/notes/{id}:
      - Hard delete a note by ID.
    """

    @blp.response(200, SingleNoteResponseSchema, description="Get a note by ID")
    def get(self, note_id: str):
        """
        Retrieve note by ID.
        """
        storage = get_storage()
        note = storage.get_note(note_id)
        if not note:
            abort(404, message="Note not found")
        return {"data": note}

    @blp.arguments(NoteUpdatePutSchema)
    @blp.response(200, SingleNoteResponseSchema, description="Updated note (PUT)")
    def put(self, json_data: Dict[str, Any], note_id: str):
        """
        Full update of a note by ID (PUT).
        """
        storage = get_storage()
        if storage.get_note(note_id) is None:
            abort(404, message="Note not found")
        try:
            note = storage.update_note(note_id, json_data)
        except ValueError as e:
            abort(400, message=str(e))
        if not note:
            abort(404, message="Note not found")
        return {"data": note}

    @blp.arguments(NoteUpdatePatchSchema)
    @blp.response(200, SingleNoteResponseSchema, description="Updated note (PATCH)")
    def patch(self, json_data: Dict[str, Any], note_id: str):
        """
        Partial update of a note by ID (PATCH).
        """
        storage = get_storage()
        existing = storage.get_note(note_id)
        if not existing:
            abort(404, message="Note not found")
        # Merge patch over existing (service handles defaults and validation)
        update_data: Dict[str, Any] = {**existing, **json_data}  # type: ignore
        try:
            note = storage.update_note(note_id, update_data)
        except ValueError as e:
            abort(400, message=str(e))
        if not note:
            abort(404, message="Note not found")
        return {"data": note}

    @blp.response(204, description="Note deleted")
    def delete(self, note_id: str):
        """
        Delete a note by ID.
        """
        storage = get_storage()
        ok = storage.delete_note(note_id)
        if not ok:
            abort(404, message="Note not found")
        return ""  # 204 No Content


@blp.route("/<string:note_id>/archive")
class NoteArchive(MethodView):
    """
    PUBLIC_INTERFACE
    Archive a note.

    POST /api/notes/{id}/archive:
      - Soft-archives the note by setting archived=true.
    """

    @blp.response(200, SingleNoteResponseSchema, description="Archived note")
    def post(self, note_id: str):
        """
        Archive a note by ID.
        """
        storage = get_storage()
        # Ensure existence
        if not storage.get_note(note_id):
            abort(404, message="Note not found")

        note = storage.soft_archive(note_id)
        if not note:
            abort(404, message="Note not found")
        return {"data": note}


@blp.route("/<string:note_id>/restore")
class NoteRestore(MethodView):
    """
    PUBLIC_INTERFACE
    Restore an archived note.

    POST /api/notes/{id}/restore:
      - Sets archived=false for the note.
    """

    @blp.response(200, SingleNoteResponseSchema, description="Restored note")
    def post(self, note_id: str):
        """
        Restore a note by ID (sets archived to False).
        """
        storage = get_storage()
        note = storage.get_note(note_id)
        if not note:
            abort(404, message="Note not found")

        # Use update_note to flip archived to False
        updated = storage.update_note(note_id, {**note, "archived": False})  # type: ignore[arg-type]
        if not updated:
            abort(404, message="Note not found")
        return {"data": updated}
