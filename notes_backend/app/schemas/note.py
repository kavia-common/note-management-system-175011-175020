"""
Marshmallow schemas for Notes API.

These schemas are designed to work with flask-smorest for request parsing and
OpenAPI generation. They cover:
- Pagination metadata
- Note entity serialization
- Create and Update request bodies (PUT/PATCH)
- List response with pagination metadata
- Single note response envelope
- Common list query args schema
"""

from marshmallow import Schema, fields, validate, EXCLUDE


class PaginationMetadataSchema(Schema):
    """
    PUBLIC_INTERFACE
    Common pagination metadata schema used in list/search endpoints.

    Fields:
    - total: total number of items across all pages
    - total_pages: total number of pages given the page_size
    - first_page: first page index (usually 1)
    - last_page: last page index (equal to total_pages or 0 when empty)
    - page: current page index
    - previous_page: previous page index or 0 if none
    - next_page: next page index or 0 if none
    """

    total = fields.Int(required=True, metadata={"description": "Total number of items"})
    total_pages = fields.Int(required=True, metadata={"description": "Total number of pages"})
    first_page = fields.Int(required=True, metadata={"description": "First page index"})
    last_page = fields.Int(required=True, metadata={"description": "Last page index"})
    page = fields.Int(required=True, metadata={"description": "Current page index"})
    previous_page = fields.Int(required=True, metadata={"description": "Previous page index or 0"})
    next_page = fields.Int(required=True, metadata={"description": "Next page index or 0"})

    class Meta:
        ordered = True


class NoteSchema(Schema):
    """
    PUBLIC_INTERFACE
    Output schema for a Note entity.

    Fields reflect the persisted model and are read-only for output serialization.
    """

    id = fields.String(
        required=True,
        dump_only=True,
        metadata={"description": "UUID of the note"},
    )
    title = fields.String(
        required=True,
        metadata={"description": "Title of the note"},
    )
    content = fields.String(
        required=True,
        metadata={"description": "Content of the note"},
    )
    # We store tags as comma-separated string in DB; accept list or string in inputs with create/update schemas.
    tags = fields.String(
        allow_none=True,
        metadata={"description": "Comma-separated tags"},
    )
    archived = fields.Boolean(
        required=True,
        metadata={"description": "Whether the note is archived"},
    )
    created_at = fields.String(
        required=True,
        dump_only=True,
        metadata={"description": "Creation timestamp (ISO8601, UTC)"},
    )
    updated_at = fields.String(
        required=True,
        dump_only=True,
        metadata={"description": "Last update timestamp (ISO8601, UTC)"},
    )

    class Meta:
        ordered = True


class _TagsField(fields.Field):
    """
    Custom field to accept tags as either:
    - list of strings
    - string (comma-separated)

    On load, returns either None or a list[str].
    On dump, leave serialization to NoteSchema as a string; this field is for input schemas.
    """

    def _deserialize(self, value, attr, data, **kwargs):
        if value is None or value == "":
            return None
        if isinstance(value, list):
            # Normalize to list of trimmed strings
            return [str(v).strip() for v in value if str(v).strip() != ""]
        # Assume string: split by comma
        return [part.strip() for part in str(value).split(",") if part.strip() != ""]


class NoteCreateSchema(Schema):
    """
    PUBLIC_INTERFACE
    Request body schema for creating a note.

    Requirements:
    - title: required, non-empty
    - content: required, non-empty
    - tags: optional list[str] or comma-separated str
    - archived: optional bool (default False handled by service)
    """

    title = fields.String(
        required=True,
        validate=validate.Length(min=1),
        metadata={"description": "Title of the note"},
    )
    content = fields.String(
        required=True,
        validate=validate.Length(min=1),
        metadata={"description": "Content of the note"},
    )
    tags = _TagsField(
        required=False,
        allow_none=True,
        metadata={"description": "Tags as list of strings or comma-separated string"},
    )
    archived = fields.Boolean(
        required=False,
        load_default=False,
        metadata={"description": "Set to true to create the note as archived"},
    )

    class Meta:
        ordered = True
        unknown = EXCLUDE


class NoteUpdatePutSchema(Schema):
    """
    PUBLIC_INTERFACE
    Request body schema for fully updating a note (PUT semantics).

    All fields are required and replace the existing values.
    """

    title = fields.String(
        required=True,
        validate=validate.Length(min=1),
        metadata={"description": "Title of the note"},
    )
    content = fields.String(
        required=True,
        validate=validate.Length(min=1),
        metadata={"description": "Content of the note"},
    )
    tags = _TagsField(
        required=False,
        allow_none=True,
        metadata={"description": "Tags as list of strings or comma-separated string"},
    )
    archived = fields.Boolean(
        required=True,
        metadata={"description": "Whether the note is archived"},
    )

    class Meta:
        ordered = True
        unknown = EXCLUDE


class NoteUpdatePatchSchema(Schema):
    """
    PUBLIC_INTERFACE
    Request body schema for partially updating a note (PATCH semantics).

    All fields are optional; only provided fields will be updated.
    """

    title = fields.String(
        required=False,
        validate=validate.Length(min=1),
        metadata={"description": "Title of the note"},
    )
    content = fields.String(
        required=False,
        validate=validate.Length(min=1),
        metadata={"description": "Content of the note"},
    )
    tags = _TagsField(
        required=False,
        allow_none=True,
        metadata={"description": "Tags as list of strings or comma-separated string"},
    )
    archived = fields.Boolean(
        required=False,
        metadata={"description": "Whether the note is archived"},
    )

    class Meta:
        ordered = True
        unknown = EXCLUDE


class NotesListQueryArgsSchema(Schema):
    """
    PUBLIC_INTERFACE
    Query parameters for listing notes.

    Supports:
    - page, page_size
    - archived (defaults False)
    - tag (filter by tag contained in tags CSV)
    - created_from, created_to, updated_from, updated_to (ISO strings)
    """

    page = fields.Int(load_default=1, validate=validate.Range(min=1), metadata={"description": "Page number (1-based)"})
    page_size = fields.Int(load_default=20, validate=validate.Range(min=1, max=100), metadata={"description": "Items per page"})
    archived = fields.Boolean(load_default=False, metadata={"description": "Include archived notes"})
    tag = fields.String(required=False, metadata={"description": "Filter notes that include this tag"})
    created_from = fields.String(required=False, metadata={"description": "Created from timestamp (ISO8601)"})
    created_to = fields.String(required=False, metadata={"description": "Created to timestamp (ISO8601)"})
    updated_from = fields.String(required=False, metadata={"description": "Updated from timestamp (ISO8601)"})
    updated_to = fields.String(required=False, metadata={"description": "Updated to timestamp (ISO8601)"})

    class Meta:
        ordered = True
        unknown = EXCLUDE


class NotesListResponseSchema(Schema):
    """
    PUBLIC_INTERFACE
    Response envelope for a list of notes with pagination metadata.
    """

    data = fields.List(fields.Nested(NoteSchema), required=True, metadata={"description": "List of notes"})
    metadata = fields.Nested(PaginationMetadataSchema, required=True, metadata={"description": "Pagination metadata"})

    class Meta:
        ordered = True


class SingleNoteResponseSchema(Schema):
    """
    PUBLIC_INTERFACE
    Response envelope for a single note.
    """

    data = fields.Nested(NoteSchema, required=True, metadata={"description": "The requested/created/updated note"})

    class Meta:
        ordered = True
