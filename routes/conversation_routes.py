import logging
from flask import Blueprint, request, jsonify
from conversation_service import ConversationService

logger = logging.getLogger(__name__)

conversation_bp = Blueprint("conversation_routes", __name__, url_prefix="/api")


@conversation_bp.route("/conversations", methods=["POST"])
def create_conversation():
    """Create a new conversation."""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get("title", "New Conversation")
        conversation = ConversationService.create_conversation(title=title)
        return jsonify({"success": True, "conversation": conversation.to_dict(include_messages=False)}), 201
    except Exception as e:
        logger.error(f"Error creating conversation: {e}", exc_info=True)
        return jsonify({"error": "Failed to create conversation"}), 500


@conversation_bp.route("/conversations", methods=["GET"])
def get_conversations():
    """Retrieve all conversations, with optional search query (?q=term)."""
    try:
        search_query = request.args.get("q", type=str)
        conversations = ConversationService.get_all_conversations(search_query=search_query)
        return jsonify({
            "success": True,
            "conversations": [conv.to_dict(include_messages=False) for conv in conversations],
            "count": len(conversations),
        }), 200
    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve conversations"}), 500


@conversation_bp.route("/conversations/<conversation_id>", methods=["GET"])
def get_conversation_details(conversation_id):
    """Retrieve specific conversation details and all chronological messages."""
    try:
        conversation = ConversationService.get_conversation(conversation_id)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404

        return jsonify({
            "success": True,
            "conversation": conversation.to_dict(include_messages=True),
        }), 200
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve conversation details"}), 500


@conversation_bp.route("/conversations/<conversation_id>", methods=["PATCH"])
def rename_conversation(conversation_id):
    """Rename a conversation."""
    try:
        data = request.get_json(silent=True) or {}
        new_title = data.get("title", "").strip()

        if not new_title:
            return jsonify({"error": "Title cannot be empty"}), 400

        conversation = ConversationService.update_conversation_title(conversation_id, new_title)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404

        return jsonify({
            "success": True,
            "conversation": conversation.to_dict(include_messages=False),
        }), 200
    except Exception as e:
        logger.error(f"Error renaming conversation {conversation_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to rename conversation"}), 500


@conversation_bp.route("/conversations/<conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    """Delete a conversation and all its messages."""
    try:
        success = ConversationService.delete_conversation(conversation_id)
        if not success:
            return jsonify({"error": "Conversation not found"}), 404

        return jsonify({"success": True, "message": "Conversation deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete conversation"}), 500


@conversation_bp.route("/conversations/<conversation_id>/clear", methods=["POST"])
def clear_conversation(conversation_id):
    """Clear all messages from a conversation while keeping its ID."""
    try:
        success = ConversationService.clear_conversation_messages(conversation_id)
        if not success:
            return jsonify({"error": "Conversation not found"}), 404

        return jsonify({"success": True, "message": "Conversation cleared successfully"}), 200
    except Exception as e:
        logger.error(f"Error clearing conversation {conversation_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to clear conversation"}), 500
