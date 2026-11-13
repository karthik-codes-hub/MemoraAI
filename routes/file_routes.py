import logging
from flask import Blueprint, request, jsonify
from file_service import FileService, FileProcessingError
from conversation_service import ConversationService

logger = logging.getLogger(__name__)

file_bp = Blueprint("file_routes", __name__, url_prefix="/api")


@file_bp.route("/files/upload", methods=["POST"])
def upload_file():
    """
    Handle single or multi-file upload:
    - Validates file type and size.
    - Saves to disk securely.
    - Extracts text/tables/metadata.
    - Creates chunked segments.
    - Persists UploadedFile records in SQLite.
    """
    try:
        # Check if files part is present
        uploaded_files_list = []
        if "file" in request.files:
            uploaded_files_list.append(request.files["file"])
        elif "files" in request.files:
            uploaded_files_list.extend(request.files.getlist("files"))

        if not uploaded_files_list:
            return jsonify({"error": "No file uploaded in request"}), 400

        conversation_id = request.form.get("conversation_id")
        if conversation_id:
            # Validate conversation exists or create if requested
            conv = ConversationService.get_conversation(conversation_id)
            if not conv:
                conv = ConversationService.create_conversation("Document Chat")
                conversation_id = conv.id

        processed_files = []
        errors = []

        for f in uploaded_files_list:
            if not f or not f.filename:
                continue
            try:
                uploaded_rec = FileService.save_and_process_file(f, conversation_id=conversation_id)
                processed_files.append(uploaded_rec.to_dict(include_content=False))
            except FileProcessingError as fe:
                errors.append(f"{f.filename}: {str(fe)}")
            except Exception as e:
                logger.error(f"Unexpected error processing {f.filename}: {e}", exc_info=True)
                errors.append(f"{f.filename}: Processing failed.")

        if not processed_files and errors:
            return jsonify({"error": "; ".join(errors)}), 400

        return jsonify({
            "success": True,
            "files": processed_files,
            "errors": errors if errors else None,
            "conversation_id": conversation_id,
        }), 201

    except Exception as e:
        logger.error(f"Upload endpoint error: {e}", exc_info=True)
        return jsonify({"error": f"Failed to upload file: {str(e)}"}), 500


@file_bp.route("/files", methods=["GET"])
def get_files():
    """List uploaded files with optional search and category filters."""
    try:
        search_query = request.args.get("q", type=str)
        category = request.args.get("category", type=str)
        files = FileService.get_all_files(search_query=search_query, category=category)
        return jsonify({
            "success": True,
            "files": [f.to_dict(include_content=False) for f in files],
            "count": len(files),
        }), 200
    except Exception as e:
        logger.error(f"Error listing files: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve files"}), 500


@file_bp.route("/files/<file_id>", methods=["GET"])
def get_file_details(file_id):
    """Retrieve metadata for a specific uploaded file."""
    try:
        file_rec = FileService.get_file(file_id)
        if not file_rec:
            return jsonify({"error": "File not found"}), 404

        return jsonify({
            "success": True,
            "file": file_rec.to_dict(include_content=False),
        }), 200
    except Exception as e:
        logger.error(f"Error getting file {file_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve file details"}), 500


@file_bp.route("/files/<file_id>/content", methods=["GET"])
def get_file_content(file_id):
    """Retrieve full extracted text content of an uploaded file."""
    try:
        file_rec = FileService.get_file(file_id)
        if not file_rec:
            return jsonify({"error": "File not found"}), 404

        return jsonify({
            "success": True,
            "id": file_rec.id,
            "filename": file_rec.original_filename,
            "extracted_text": file_rec.extracted_text or "",
            "chunks": [c.to_dict() for c in file_rec.chunks],
        }), 200
    except Exception as e:
        logger.error(f"Error getting file content {file_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to retrieve file content"}), 500


@file_bp.route("/files/<file_id>", methods=["DELETE"])
def delete_file(file_id):
    """Delete an uploaded file and its stored disk data."""
    try:
        success = FileService.delete_file(file_id)
        if not success:
            return jsonify({"error": "File not found"}), 404

        return jsonify({"success": True, "message": "File deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete file"}), 500

