"""
Schemas package exposing public Marshmallow schemas for the Notes API.

This package contains:
- PaginationMetadataSchema: Common pagination metadata for list/search responses
- Note schemas: input and output schemas for note creation, update, retrieval, and listing
"""

from .note import (
    PaginationMetadataSchema,
    NoteSchema,
    NoteCreateSchema,
    NoteUpdatePutSchema,
    NoteUpdatePatchSchema,
    NotesListQueryArgsSchema,
    NotesListResponseSchema,
    SingleNoteResponseSchema,
)

__all__ = [
    # Pagination
    "PaginationMetadataSchema",
    # Note schemas
    "NoteSchema",
    "NoteCreateSchema",
    "NoteUpdatePutSchema",
    "NoteUpdatePatchSchema",
    "NotesListQueryArgsSchema",
    "NotesListResponseSchema",
    "SingleNoteResponseSchema",
]
