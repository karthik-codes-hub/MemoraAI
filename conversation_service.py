import logging
from typing import List, Optional
from datetime import datetime, timezone
from database import db
from models import Conversation, Message

logger = logging.getLogger(__name__)


class ConversationService:
    """Handles all database operations for conversations and messages."""

    @staticmethod
    def create_conversation(title: str = "New Conversation") -> Conversation:
        """Create a new conversation record."""
        conversation = Conversation(title=title.strip() or "New Conversation")
        db.session.add(conversation)
        db.session.commit()
        return conversation

    @staticmethod
    def get_conversation(conversation_id: str) -> Optional[Conversation]:
        """Fetch conversation by ID."""
        return Conversation.query.filter_by(id=conversation_id).first()

    @staticmethod
    def get_all_conversations(search_query: Optional[str] = None) -> List[Conversation]:
        """
        Fetch all conversations ordered by updated_at descending.
        Optionally filter by search query matching title or message content.
        """
        query = Conversation.query

        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            # Match title OR conversations containing matching messages
            subquery = (
                db.session.query(Message.conversation_id)
                .filter(Message.content.ilike(term))
                .distinct()
            )
            query = query.filter((Conversation.title.ilike(term)) | (Conversation.id.in_(subquery)))

        return query.order_by(Conversation.updated_at.desc()).all()

    @staticmethod
    def update_conversation_title(conversation_id: str, new_title: str) -> Optional[Conversation]:
        """Rename an existing conversation."""
        conversation = Conversation.query.filter_by(id=conversation_id).first()
        if not conversation:
            return None

        clean_title = new_title.strip()
        if clean_title:
            conversation.title = clean_title
            conversation.updated_at = datetime.now(timezone.utc)
            db.session.commit()
        return conversation

    @staticmethod
    def delete_conversation(conversation_id: str) -> bool:
        """Delete a conversation and all its cascaded messages."""
        conversation = Conversation.query.filter_by(id=conversation_id).first()
        if not conversation:
            return False

        db.session.delete(conversation)
        db.session.commit()
        return True

    @staticmethod
    def add_message(conversation_id: str, role: str, content: str) -> Message:
        """Add a new message to a conversation and update conversation updated_at."""
        conversation = Conversation.query.filter_by(id=conversation_id).first()
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        message = Message(
            conversation_id=conversation_id,
            role=role.strip().lower(),
            content=content.strip(),
        )
        conversation.updated_at = datetime.now(timezone.utc)

        db.session.add(message)
        db.session.commit()
        return message

    @staticmethod
    def get_messages(conversation_id: str) -> List[Message]:
        """Get all messages for a conversation in chronological order."""
        return (
            Message.query.filter_by(conversation_id=conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )

    @staticmethod
    def update_summary(conversation_id: str, summary: str) -> None:
        """Update the running summary of older messages for a conversation."""
        conversation = Conversation.query.filter_by(id=conversation_id).first()
        if conversation:
            conversation.summary = summary
            db.session.commit()

    @staticmethod
    def remove_last_assistant_message(conversation_id: str) -> Optional[Message]:
        """
        Removes the last message in the conversation if it was sent by the assistant.
        Used for regenerate response functionality.
        """
        last_message = (
            Message.query.filter_by(conversation_id=conversation_id)
            .order_by(Message.created_at.desc())
            .first()
        )

        if last_message and last_message.role == "assistant":
            db.session.delete(last_message)
            db.session.commit()
            return last_message
        return None

    @staticmethod
    def clear_conversation_messages(conversation_id: str) -> bool:
        """Clear all messages in a conversation while preserving the conversation itself."""
        conversation = Conversation.query.filter_by(id=conversation_id).first()
        if not conversation:
            return False

        Message.query.filter_by(conversation_id=conversation_id).delete()
        conversation.summary = None
        conversation.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return True
