import json
from unittest.mock import MagicMock
from openai_service import AIServiceError
from conversation_service import ConversationService


def test_chat_multi_turn_flow(client, mock_openai, app):
    """Test full multi-turn conversation flow with message persistence."""
    # Turn 1
    res1 = client.post("/api/chat", json={"message": "My name is Karthik."})
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert data1["success"] is True
    conv_id = data1["conversation_id"]
    assert conv_id is not None
    assert "message" in data1
    assert data1["message"]["role"] == "assistant"

    # Turn 2 in same conversation
    res2 = client.post("/api/chat", json={
        "conversation_id": conv_id,
        "message": "I am studying Computer Science and Engineering.",
    })
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["conversation_id"] == conv_id

    # Verify database holds both turns (2 user + 2 assistant = 4 messages)
    with app.app_context():
        messages = ConversationService.get_messages(conv_id)
        assert len(messages) == 4
        assert messages[0].content == "My name is Karthik."
        assert messages[2].content == "I am studying Computer Science and Engineering."


def test_chat_empty_message_validation(client):
    """Verify empty message returns 400 bad request."""
    res = client.post("/api/chat", json={"message": "   "})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_chat_regenerate_response(client, mock_openai, app):
    """Test regenerating assistant response replaces prior response without duplicating user message."""
    with app.app_context():
        c = ConversationService.create_conversation("Regenerate Test")
        ConversationService.add_message(c.id, "user", "Tell me a joke.")
        ConversationService.add_message(c.id, "assistant", "Old joke that user wants to regenerate.")
        conv_id = c.id

    # Mock custom regenerated response
    mock_choice = MagicMock()
    mock_choice.message.content = "Brand new regenerated punchline!"
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_resp.usage.prompt_tokens = 20
    mock_resp.usage.completion_tokens = 10
    mock_resp.usage.total_tokens = 30
    mock_openai.chat.completions.create.return_value = mock_resp

    res = client.post(f"/api/conversations/{conv_id}/regenerate")
    assert res.status_code == 200
    data = res.get_json()
    assert data["message"]["content"] == "Brand new regenerated punchline!"

    # Verify messages in DB: should still be exactly 2 messages (1 user, 1 new assistant)
    with app.app_context():
        messages = ConversationService.get_messages(conv_id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].content == "Brand new regenerated punchline!"


def test_chat_missing_api_key_error(client, app, monkeypatch):
    """Verify clean user-friendly error when AI API key is missing."""
    monkeypatch.setattr("openai_service.Config.OPENAI_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    app.config["OPENAI_API_KEY"] = ""
    app.config["GEMINI_API_KEY"] = ""

    res = client.post("/api/chat", json={"message": "Hello"})
    assert res.status_code == 401
    data = res.get_json()
    assert "error" in data
    assert "API key" in data["error"]
