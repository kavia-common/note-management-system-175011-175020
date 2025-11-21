import os
import sqlite3
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union


def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format without timezone."""
    return datetime.utcnow().isoformat(timespec="seconds")


@dataclass
class Note:
    """
    PUBLIC_INTERFACE
    Represents a Note entity in the system.

    Fields:
    - id: UUID4 string identifier
    - title: Title of the note
    - content: Content/body of the note
    - tags: Optional comma-separated tags string (stored as text)
    - archived: Boolean flag indicating if the note is archived (soft-deleted)
    - created_at: ISO 8601 timestamp of creation (UTC)
    - updated_at: ISO 8601 timestamp of last update (UTC)
    """
    id: str
    title: str
    content: str
    tags: Optional[str] = None
    archived: bool = False
    created_at: str = ""
    updated_at: str = ""

    # PUBLIC_INTERFACE
    @staticmethod
    def from_row(row: sqlite3.Row) -> "Note":
        """Create a Note from a sqlite3.Row."""
        return Note(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            tags=row["tags"],
            archived=bool(row["archived"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # PUBLIC_INTERFACE
    def to_dict(self) -> Dict[str, Any]:
        """Convert Note to a serializable dict."""
        d = asdict(self)
        # Ensure booleans stay booleans for JSON serialization
        d["archived"] = bool(self.archived)
        return d


class StorageService:
    """
    PUBLIC_INTERFACE
    SQLite-backed storage service for Notes.

    Uses built-in sqlite3. Default DB path is 'instance/notes.db', which can be
    overridden using the NOTES_DB_PATH environment variable.

    Provides:
    - list_notes(filters, pagination)
    - get_note(id)
    - create_note(data)
    - update_note(id, data)
    - delete_note(id)
    - soft_archive(id)
    - search(query)
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        instance_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "instance")
        instance_dir = os.path.abspath(instance_dir)
        os.makedirs(instance_dir, exist_ok=True)

        env_path = os.getenv("NOTES_DB_PATH")
        self.db_path = db_path or env_path or os.path.join(instance_dir, "notes.db")

        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                  id TEXT PRIMARY KEY,
                  title TEXT NOT NULL,
                  content TEXT NOT NULL,
                  tags TEXT NULL,
                  archived INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                """
            )
            conn.commit()

    # PUBLIC_INTERFACE
    def list_notes(
        self,
        filters: Optional[Dict[str, Any]] = None,
        pagination: Optional[Dict[str, int]] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        List notes with optional filters and pagination.

        Filters supported:
        - archived: bool (default False)
        - tag: str (filter notes containing this tag in 'tags' CSV)
        - created_from: ISO str
        - created_to: ISO str
        - updated_from: ISO str
        - updated_to: ISO str

        Pagination:
        - page: int (1-based)
        - page_size: int

        Returns:
        - (notes_list, pagination_metadata)
        """
        filters = filters or {}
        pagination = pagination or {}
        page = max(1, int(pagination.get("page", 1)))
        page_size = max(1, min(100, int(pagination.get("page_size", 20))))
        params: List[Any] = []
        where: List[str] = []

        archived = filters.get("archived", False)
        where.append("archived = ?")
        params.append(1 if archived else 0)

        tag = filters.get("tag")
        if tag:
            where.append("(tags LIKE ? OR tags LIKE ? OR tags = ?)")
            params.extend([f"{tag},%", f"%,{tag}", tag])

        created_from = filters.get("created_from")
        if created_from:
            where.append("created_at >= ?")
            params.append(created_from)
        created_to = filters.get("created_to")
        if created_to:
            where.append("created_at <= ?")
            params.append(created_to)

        updated_from = filters.get("updated_from")
        if updated_from:
            where.append("updated_at >= ?")
            params.append(updated_from)
        updated_to = filters.get("updated_to")
        if updated_to:
            where.append("updated_at <= ?")
            params.append(updated_to)

        where_clause = " AND ".join(where) if where else "1=1"

        with self._get_conn() as conn:
            # Count total
            count_sql = f"SELECT COUNT(*) as cnt FROM notes WHERE {where_clause}"
            cur = conn.execute(count_sql, params)
            total = int(cur.fetchone()["cnt"])

            total_pages = (total + page_size - 1) // page_size if total > 0 else 1
            offset = (page - 1) * page_size

            sql = f"""
                SELECT id, title, content, tags, archived, created_at, updated_at
                FROM notes
                WHERE {where_clause}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?;
            """
            cur = conn.execute(sql, [*params, page_size, offset])
            rows = cur.fetchall()

        notes = [Note.from_row(r).to_dict() for r in rows]
        metadata = {
            "total": total,
            "total_pages": total_pages,
            "first_page": 1 if total > 0 else 0,
            "last_page": total_pages if total > 0 else 0,
            "page": page,
            "previous_page": page - 1 if page > 1 else 0,
            "next_page": page + 1 if page < total_pages else 0,
        }
        return notes, metadata

    # PUBLIC_INTERFACE
    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a note by ID, returns None if not found."""
        with self._get_conn() as conn:
            cur = conn.execute(
                """
                SELECT id, title, content, tags, archived, created_at, updated_at
                FROM notes WHERE id = ?;
                """,
                (note_id,),
            )
            row = cur.fetchone()
            return Note.from_row(row).to_dict() if row else None

    # PUBLIC_INTERFACE
    def create_note(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new note from provided data."""
        new_id = str(uuid.uuid4())
        now = _now_iso()
        title = str(data.get("title", "")).strip()
        content = str(data.get("content", "")).strip()
        if not title:
            raise ValueError("Title is required")
        if not content:
            raise ValueError("Content is required")
        tags_val = data.get("tags")
        tags = None if tags_val in (None, "", []) else (
            ",".join(tags_val) if isinstance(tags_val, list) else str(tags_val)
        )
        archived = bool(data.get("archived", False))

        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO notes (id, title, content, tags, archived, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (new_id, title, content, tags, 1 if archived else 0, now, now),
            )
            conn.commit()

        return self.get_note(new_id)  # type: ignore

    # PUBLIC_INTERFACE
    def update_note(self, note_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing note. Returns updated note or None if not found."""
        existing = self.get_note(note_id)
        if not existing:
            return None

        title = str(data.get("title", existing["title"])).strip()
        content = str(data.get("content", existing["content"])).strip()
        if not title:
            raise ValueError("Title is required")
        if not content:
            raise ValueError("Content is required")

        tags_val = data.get("tags", existing.get("tags"))
        tags = None if tags_val in (None, "", []) else (
            ",".join(tags_val) if isinstance(tags_val, list) else str(tags_val)
        )
        archived = bool(data.get("archived", existing.get("archived", False)))
        now = _now_iso()

        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE notes
                   SET title = ?, content = ?, tags = ?, archived = ?, updated_at = ?
                 WHERE id = ?;
                """,
                (title, content, tags, 1 if archived else 0, now, note_id),
            )
            conn.commit()

        return self.get_note(note_id)  # type: ignore

    # PUBLIC_INTERFACE
    def delete_note(self, note_id: str) -> bool:
        """Hard delete a note. Returns True if a row was deleted."""
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM notes WHERE id = ?;", (note_id,))
            conn.commit()
            return cur.rowcount > 0

    # PUBLIC_INTERFACE
    def soft_archive(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Soft-archive a note by setting archived = True. Returns updated note or None."""
        existing = self.get_note(note_id)
        if not existing:
            return None
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE notes SET archived = 1, updated_at = ? WHERE id = ?;",
                (_now_iso(), note_id),
            )
            conn.commit()
        return self.get_note(note_id)  # type: ignore

    # PUBLIC_INTERFACE
    def soft_restore(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Restore a soft-archived note by setting archived = False. Returns updated note or None."""
        existing = self.get_note(note_id)
        if not existing:
            return None
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE notes SET archived = 0, updated_at = ? WHERE id = ?;",
                (_now_iso(), note_id),
            )
            conn.commit()
        return self.get_note(note_id)  # type: ignore

    # PUBLIC_INTERFACE
    def search(self, query: str, include_archived: bool = False, page: int = 1, page_size: int = 20) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Simple LIKE-based search across title, content, and tags.

        Args:
        - query: search string
        - include_archived: include archived notes if True
        - page: page number (1-based)
        - page_size: number of items per page

        Returns:
        - (notes_list, pagination_metadata)
        """
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        like = f"%{query}%"

        where = ["(title LIKE ? OR content LIKE ? OR IFNULL(tags, '') LIKE ?)"]
        params: List[Union[str, int]] = [like, like, like]
        if not include_archived:
            where.append("archived = 0")
        where_clause = " AND ".join(where)

        with self._get_conn() as conn:
            count_sql = f"SELECT COUNT(*) as cnt FROM notes WHERE {where_clause};"
            cur = conn.execute(count_sql, params)
            total = int(cur.fetchone()["cnt"])

            total_pages = (total + page_size - 1) // page_size if total > 0 else 1
            offset = (page - 1) * page_size

            sql = f"""
                SELECT id, title, content, tags, archived, created_at, updated_at
                  FROM notes
                 WHERE {where_clause}
              ORDER BY updated_at DESC
                 LIMIT ? OFFSET ?;
            """
            cur = conn.execute(sql, [*params, page_size, offset])
            rows = cur.fetchall()

        notes = [Note.from_row(r).to_dict() for r in rows]
        metadata = {
            "total": total,
            "total_pages": total_pages,
            "first_page": 1 if total > 0 else 0,
            "last_page": total_pages if total > 0 else 0,
            "page": page,
            "previous_page": page - 1 if page > 1 else 0,
            "next_page": page + 1 if page < total_pages else 0,
        }
        return notes, metadata
