import logging
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from database import db
from config import Config
from conversation_service import ConversationService
from context_manager import ContextManager
from openai_service import OpenAIService, AIServiceError

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat_routes", __name__, url_prefix="/api")


@chat_bp.route("/chat", methods=["POST"])
def send_chat_message():
    """
    Handle a user message:
    1. Validates request and message.
    2. Retrieves or creates conversation.
    3. Persists user message in SQLite.
    4. Evaluates running summary threshold.
    5. Builds token-budgeted context window with ContextManager.
    6. Calls OpenAI Chat Completions API.
    7. Persists assistant response in SQLite.
    8. Auto-generates conversation title on first turn.
    9. Returns contextual AI response.
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        user_message_text = data.get("message", "").strip()
        conversation_id = data.get("conversation_id")

        if not user_message_text:
            return jsonify({"error": "Message content cannot be empty"}), 400

        if len(user_message_text) > 20000:
            return jsonify({"error": "Message exceeds maximum allowed character length"}), 400

        # Retrieve or create conversation
        if conversation_id:
            conversation = ConversationService.get_conversation(conversation_id)
            if not conversation:
                # If non-existent conversation_id provided, create a fresh one
                conversation = ConversationService.create_conversation()
                conversation_id = conversation.id
        else:
            conversation = ConversationService.create_conversation()
            conversation_id = conversation.id

        # 1. Save user message to database
        user_message = ConversationService.add_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message_text,
        )

        # 2. Retrieve complete conversation history for context building
        all_messages = ConversationService.get_messages(conversation_id)
        formatted_messages = [
            {"role": m.role, "content": m.content} for m in all_messages
        ]

        # 3. Running Summary check and update
        context_mgr = ContextManager()
        openai_svc = OpenAIService()

        # If conversation is getting long, update the running summary of older turns
        if context_mgr.needs_summarization(len(formatted_messages), conversation.summary):
            messages_to_summarize = context_mgr.get_messages_to_summarize(formatted_messages)
            if messages_to_summarize and openai_svc.is_configured():
                try:
                    new_summary = openai_svc.generate_summary(
                        messages_to_summarize, conversation.summary
                    )
                    if new_summary:
                        ConversationService.update_summary(conversation_id, new_summary)
                        conversation.summary = new_summary
                except Exception as sum_err:
                    logger.warning(f"Failed to update conversation summary: {sum_err}")

        # 4. Construct token-budgeted context messages for LLM
        context_messages = context_mgr.build_context_messages(
            system_prompt=Config.SYSTEM_PROMPT,
            recent_messages=formatted_messages,
            summary=conversation.summary,
        )

        # 5. Call OpenAI API for completion
        ai_response_text, usage = openai_svc.generate_chat_response(context_messages)

        # 6. Save assistant response to database
        assistant_message = ConversationService.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_response_text,
        )

        # 7. Auto-generate conversation title if it's the first exchange
        if conversation.title in ("New Conversation", "New Chat", "") and len(all_messages) <= 2:
            try:
                new_title = openai_svc.generate_title(user_message_text)
                if new_title and new_title != conversation.title:
                    ConversationService.update_conversation_title(conversation_id, new_title)
                    conversation.title = new_title
            except Exception as title_err:
                logger.debug(f"Title auto-generation error: {title_err}")

        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "conversation_title": conversation.title,
            "message": assistant_message.to_dict(),
            "usage": usage,
        }), 200

    except AIServiceError as ai_err:
        logger.error(f"AI Service Error: {ai_err.message}")
        return jsonify({
            "error": ai_err.message,
            "conversation_id": conversation_id if "conversation_id" in locals() else None,
        }), ai_err.status_code

    except Exception as e:
        logger.error(f"Unexpected chat endpoint error: {e}", exc_info=True)
        return jsonify({
            "error": "Something went wrong. Your previous conversation has been preserved.",
            "conversation_id": conversation_id if "conversation_id" in locals() else None,
        }), 500


@chat_bp.route("/conversations/<conversation_id>/regenerate", methods=["POST"])
def regenerate_response(conversation_id):
    """
    Regenerate the latest assistant response:
    1. Removes the prior assistant message.
    2. Uses existing prior user prompt and context.
    3. Requests a fresh completion from OpenAI.
    4. Persists the new assistant response.
    """
    try:
        conversation = ConversationService.get_conversation(conversation_id)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404

        # Remove the previous assistant message if present
        ConversationService.remove_last_assistant_message(conversation_id)

        # Fetch remaining messages (the last one is now the user's prompt)
        remaining_messages = ConversationService.get_messages(conversation_id)
        if not remaining_messages:
            return jsonify({"error": "No messages in conversation to regenerate"}), 400

        formatted_messages = [
            {"role": m.role, "content": m.content} for m in remaining_messages
        ]

        # Build context
        context_mgr = ContextManager()
        openai_svc = OpenAIService()

        context_messages = context_mgr.build_context_messages(
            system_prompt=Config.SYSTEM_PROMPT,
            recent_messages=formatted_messages,
            summary=conversation.summary,
        )

        # Call OpenAI API
        ai_response_text, usage = openai_svc.generate_chat_response(context_messages)

        # Save regenerated assistant message
        assistant_message = ConversationService.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_response_text,
        )

        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "message": assistant_message.to_dict(),
            "usage": usage,
        }), 200

    except AIServiceError as ai_err:
        logger.error(f"AI Service Error during regenerate: {ai_err.message}")
        return jsonify({"error": ai_err.message}), ai_err.status_code

    except Exception as e:
        logger.error(f"Unexpected error during regenerate for {conversation_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to regenerate response. Please try again."}), 500


@chat_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify backend, database, and AI service configuration."""
    db_status = "connected"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    openai_configured = OpenAIService().is_configured()

    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "openai_configured": openai_configured,
        "model": Config.OPENAI_MODEL,
        "max_context_tokens": Config.MAX_CONTEXT_TOKENS,
        "max_recent_messages": Config.MAX_RECENT_MESSAGES,
    }), 200
