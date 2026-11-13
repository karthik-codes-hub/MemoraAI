import uuid
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

    def to_dict(self, include_messages: bool = False) -> dict:
        """Serialize Conversation to dictionary."""
        data = {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "summary": self.summary,
            "message_count": len(self.messages),
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
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        """Serialize Message to dictionary."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
