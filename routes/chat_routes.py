import json
import logging
from flask import Blueprint, request, jsonify, Response
from sqlalchemy import text
from database import db
from config import Config
from conversation_service import ConversationService
from context_manager import ContextManager
from openai_service import OpenAIService, AIServiceError
from file_service import FileService
from models import UploadedFile

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat_routes", __name__, url_prefix="/api")


@chat_bp.route("/chat", methods=["POST"])
def send_chat_message():
    """
    Handle a user message with multi-turn memory and document intelligence:
    1. Validates request and message.
    2. Retrieves or creates conversation.
    3. Handles attached file IDs, linking them to conversation.
    4. Retrieves extracted document text / image context.
    5. Persists user message with attachment metadata.
    6. Builds token-budgeted context with system prompt, summary, and document context.
    7. Calls OpenAI / Gemini API.
    8. Persists assistant response.
    9. Auto-generates conversation title on first turn.
    """
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Request body must be valid JSON"}), 400

        user_message_text = data.get("message", "").strip()
        conversation_id = data.get("conversation_id")
        file_ids = data.get("file_ids", [])  # list of uploaded file IDs

        if not user_message_text and not file_ids:
            return jsonify({"error": "Message content or file attachment is required"}), 400

        if len(user_message_text) > 25000:
            return jsonify({"error": "Message exceeds maximum allowed character length"}), 400

        # Retrieve or create conversation
        if conversation_id:
            conversation = ConversationService.get_conversation(conversation_id)
            if not conversation:
                conversation = ConversationService.create_conversation("New Conversation")
                conversation_id = conversation.id
        else:
            conversation = ConversationService.create_conversation("New Conversation")
            conversation_id = conversation.id

        # 1. Process and associate any attached files
        attachment_metadata = []
        document_context = ""
        image_attachments = []

        if file_ids:
            # Associate files with this conversation
            for fid in file_ids:
                f_rec = FileService.get_file(fid)
                if f_rec:
                    if not f_rec.conversation_id:
                        f_rec.conversation_id = conversation_id
                        db.session.commit()
                    attachment_metadata.append({
                        "id": f_rec.id,
                        "filename": f_rec.original_filename,
                        "category": f_rec.file_category,
                        "size": f_rec.file_size,
                    })
                    if f_rec.file_category == "image":
                        image_attachments.append(f_rec)

            # Build extracted document text context
            document_context = FileService.get_file_content_context(
                file_ids, max_chars=Config.MAX_DOCUMENT_CONTEXT_CHARS
            )

        # 2. Save user message to database
        user_message = ConversationService.add_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message_text or "[Attached Files]",
        )
        if attachment_metadata:
            user_message.attachments_json = json.dumps(attachment_metadata)
            db.session.commit()

        # 3. Retrieve complete conversation history for context building
        all_messages = ConversationService.get_messages(conversation_id)
        formatted_messages = [
            {"role": m.role, "content": m.content} for m in all_messages
        ]

        # 4. Running Summary check and update
        context_mgr = ContextManager()
        openai_svc = OpenAIService()

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

        # 5. Construct token-budgeted context messages for LLM
        context_messages = context_mgr.build_context_messages(
            system_prompt=Config.SYSTEM_PROMPT,
            recent_messages=formatted_messages,
            summary=conversation.summary,
        )

        # 6. Inject Document Intelligence Context if documents are attached
        if document_context:
            doc_context_message = {
                "role": "system",
                "content": (
                    "DOCUMENT INTELLIGENCE CONTEXT (Attached Files Data & Structure):\n"
                    "The user has uploaded files. Use the extracted information below as the definitive ground truth "
                    "when answering the user's questions. Always cite the file name, page numbers, spreadsheet sheets, "
                    "or slide numbers where relevant.\n\n"
                    f"{document_context}"
                ),
            }
            # Insert right after base system prompt (index 1)
            context_messages.insert(1, doc_context_message)

        # 7. Call OpenAI / Gemini API for completion
        ai_response_text, usage = openai_svc.generate_chat_response(context_messages)

        # 8. Save assistant response to database
        assistant_message = ConversationService.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_response_text,
        )

        # 9. Auto-generate conversation title if it's the first exchange
        if conversation.title in ("New Conversation", "New Chat", "Document Chat", "") and len(all_messages) <= 2:
            try:
                title_basis = user_message_text
                if not title_basis and attachment_metadata:
                    title_basis = f"Analysis of {attachment_metadata[0]['filename']}"
                new_title = openai_svc.generate_title(title_basis)
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
    2. Reconstructs context including file context if files were attached.
    3. Requests a fresh completion from the AI provider.
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

        # Check for associated conversation files
        conv_files = FileService.get_conversation_files(conversation_id)
        doc_context = ""
        if conv_files:
            file_ids = [f.id for f in conv_files]
            doc_context = FileService.get_file_content_context(file_ids)

        context_mgr = ContextManager()
        openai_svc = OpenAIService()

        context_messages = context_mgr.build_context_messages(
            system_prompt=Config.SYSTEM_PROMPT,
            recent_messages=formatted_messages,
            summary=conversation.summary,
        )

        if doc_context:
            doc_context_message = {
                "role": "system",
                "content": (
                    "DOCUMENT INTELLIGENCE CONTEXT:\n"
                    f"{doc_context}"
                ),
            }
            context_messages.insert(1, doc_context_message)

        # Call AI API
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


@chat_bp.route("/conversations/<conversation_id>/export", methods=["GET"])
def export_conversation(conversation_id):
    """Export conversation transcript in Markdown or JSON format."""
    try:
        conversation = ConversationService.get_conversation(conversation_id)
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404

        export_format = request.args.get("format", "markdown").lower()

        if export_format == "json":
            return jsonify({
                "success": True,
                "conversation": conversation.to_dict(include_messages=True, include_files=True),
            }), 200

        # Markdown format
        md_lines = [
            f"# {conversation.title}",
            f"*Exported from MemoraAI on {conversation.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}*",
            f"**Tagline**: Every Conversation Matters. Every Memory Counts.",
            "\n---\n",
        ]

        for msg in conversation.messages:
            sender = "User" if msg.role == "user" else "MemoraAI"
            time_str = msg.created_at.strftime("%H:%M") if msg.created_at else ""
            md_lines.append(f"### {sender} ({time_str})\n")
            md_lines.append(f"{msg.content}\n")

        md_content = "\n".join(md_lines)
        filename = f"{conversation.title.replace(' ', '_')[:30]}_export.md"

        return Response(
            md_content,
            mimetype="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        logger.error(f"Error exporting conversation {conversation_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to export conversation"}), 500


@chat_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify backend, database, and AI service configuration."""
    db_status = "connected"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    openai_svc = OpenAIService()

    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "app_name": Config.APP_NAME,
        "version": Config.VERSION,
        "database": db_status,
        "provider": "google-gemini" if openai_svc.is_gemini else "openai",
        "openai_configured": openai_svc.is_configured(),
        "model": openai_svc.model,
        "max_context_tokens": Config.MAX_CONTEXT_TOKENS,
        "max_recent_messages": Config.MAX_RECENT_MESSAGES,
        "max_upload_size_mb": Config.MAX_CONTENT_LENGTH // (1024 * 1024),
    }), 200
