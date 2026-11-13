import uuid
import json
from datetime import datetime, timezone
from database import db


def generate_uuid() -> str:
    """Generate a unique string UUID."""
    return str(uuid.uuid4())


class Conversation(db.Model):
    """Model representing a conversation thread."""

    __tablename__ = "conversations"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    title = db.Column(db.String(255), nullable=False, default="New Conversation")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    summary = db.Column(db.Text, nullable=True)

    # Cascade delete messages when conversation is deleted
    messages = db.relationship(
        "Message",
        backref="conversation",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="Message.created_at.asc()",
    )

    # Associated uploaded files with cascade deletion
    files = db.relationship(
        "UploadedFile",
        backref="conversation",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="UploadedFile.created_at.desc()",
    )

    def to_dict(self, include_messages: bool = False, include_files: bool = True) -> dict:
        """Serialize Conversation to dictionary."""
        data = {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "summary": self.summary,
            "message_count": len(self.messages),
            "file_count": len(self.files),
        }

        # Include snippet of last message if available
        if self.messages:
            last_msg = self.messages[-1]
            data["last_message"] = {
                "role": last_msg.role,
                "content": last_msg.content[:120] + ("..." if len(last_msg.content) > 120 else ""),
                "created_at": last_msg.created_at.isoformat() if last_msg.created_at else None,
            }
        else:
            data["last_message"] = None

        if include_files:
            data["files"] = [f.to_dict(include_content=False) for f in self.files]

        if include_messages:
            data["messages"] = [msg.to_dict() for msg in self.messages]

        return data


class Message(db.Model):
    """Model representing an individual message in a conversation."""

    __tablename__ = "messages"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    conversation_id = db.Column(
        db.String(36),
        db.ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = db.Column(db.String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = db.Column(db.Text, nullable=False)
    # JSON-encoded array of attached file metadata (e.g. [{"id": ..., "filename": ..., "size": ...}])
    attachments_json = db.Column(db.Text, nullable=True, default=None)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        """Serialize Message to dictionary."""
        attachments = []
        if self.attachments_json:
            try:
                attachments = json.loads(self.attachments_json)
            except Exception:
                attachments = []

        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "attachments": attachments,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UploadedFile(db.Model):
    """Model representing an uploaded document, spreadsheet, presentation, or image."""

    __tablename__ = "uploaded_files"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    conversation_id = db.Column(
        db.String(36),
        db.ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    storage_path = db.Column(db.String(500), nullable=False)
    file_category = db.Column(db.String(30), nullable=False, default="document")  # document, spreadsheet, presentation, image, text
    extracted_text = db.Column(db.Text, nullable=True)
    processing_status = db.Column(db.String(30), nullable=False, default="completed")  # pending, processing, completed, failed
    error_message = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)  # page count, sheet names, dimensions, etc.
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Document text chunks
    chunks = db.relationship(
        "DocumentChunk",
        backref="file",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index.asc()",
    )

    def to_dict(self, include_content: bool = False) -> dict:
        """Serialize UploadedFile to dictionary."""
        metadata = {}
        if self.metadata_json:
            try:
                metadata = json.loads(self.metadata_json)
            except Exception:
                metadata = {}

        data = {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "file_category": self.file_category,
            "processing_status": self.processing_status,
            "error_message": self.error_message,
            "chunk_count": len(self.chunks),
            "metadata": metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

        if include_content:
            data["extracted_text"] = self.extracted_text

        return data


class DocumentChunk(db.Model):
    """Model representing a chunked segment of an extracted document for targeted context retrieval."""

    __tablename__ = "document_chunks"

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    file_id = db.Column(
        db.String(36),
        db.ForeignKey("uploaded_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    page_number = db.Column(db.Integer, nullable=True)
    section_title = db.Column(db.String(255), nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        """Serialize DocumentChunk to dictionary."""
        return {
            "id": self.id,
            "file_id": self.file_id,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
