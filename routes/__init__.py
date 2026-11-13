from flask import Blueprint

chat_bp = Blueprint("chat", __name__, url_prefix="/api")
conversation_bp = Blueprint("conversations", __name__, url_prefix="/api")
