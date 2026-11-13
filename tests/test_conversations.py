import json
from conversation_service import ConversationService


def test_health_check(client):
    """Test health check returns healthy status and DB connection."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] in ("healthy", "degraded")
    assert data["database"] == "connected"
    assert "model" in data


def test_create_conversation(client):
    """Test creating a new conversation with custom and default titles."""
    # Default title
    res1 = client.post("/api/conversations", json={})
    assert res1.status_code == 201
    data1 = res1.get_json()
    assert data1["success"] is True
    assert data1["conversation"]["title"] == "New Conversation"
    assert "id" in data1["conversation"]

    # Custom title
    res2 = client.post("/api/conversations", json={"title": "AI Research Project"})
    assert res2.status_code == 201
    data2 = res2.get_json()
    assert data2["conversation"]["title"] == "AI Research Project"


def test_get_conversations_and_search(client, app):
    """Test listing conversations and searching by title or message content."""
    with app.app_context():
        c1 = ConversationService.create_conversation("Python Programming")
        c2 = ConversationService.create_conversation("Database Architecture")
        c1_id = c1.id
        c2_id = c2.id
        ConversationService.add_message(c1_id, "user", "Explain decorators in Python")
        ConversationService.add_message(c2_id, "user", "How to index SQLite efficiently")

    # List all
    res = client.get("/api/conversations")
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] >= 2

    # Search by title
    res_search = client.get("/api/conversations?q=Python")
    data_search = res_search.get_json()
    assert len(data_search["conversations"]) == 1
    assert data_search["conversations"][0]["title"] == "Python Programming"

    # Search by message content
    res_msg_search = client.get("/api/conversations?q=decorators")
    data_msg_search = res_msg_search.get_json()
    assert len(data_msg_search["conversations"]) == 1
    assert data_msg_search["conversations"][0]["id"] == c1_id


def test_get_conversation_details(client, app):
    """Test retrieving conversation details including chronological message history."""
    with app.app_context():
        c = ConversationService.create_conversation("Multi-turn Chat")
        conv_id = c.id
        ConversationService.add_message(conv_id, "user", "Hello ContextAI")
        ConversationService.add_message(conv_id, "assistant", "Hello! How can I assist you today?")

    res = client.get(f"/api/conversations/{conv_id}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["conversation"]["messages"]) == 2
    assert data["conversation"]["messages"][0]["role"] == "user"
    assert data["conversation"]["messages"][1]["role"] == "assistant"


def test_rename_conversation(client, app):
    """Test renaming a conversation via PATCH."""
    with app.app_context():
        c = ConversationService.create_conversation("Old Title")
        conv_id = c.id

    res = client.patch(f"/api/conversations/{conv_id}", json={"title": "Updated Modern Title"})
    assert res.status_code == 200
    assert res.get_json()["conversation"]["title"] == "Updated Modern Title"

    # Empty title error
    res_empty = client.patch(f"/api/conversations/{conv_id}", json={"title": "  "})
    assert res_empty.status_code == 400


def test_delete_conversation_cascading(client, app):
    """Test deleting conversation cascades and deletes all child messages."""
    with app.app_context():
        c = ConversationService.create_conversation("To be deleted")
        conv_id = c.id
        ConversationService.add_message(conv_id, "user", "Ephemeral message")

    del_res = client.delete(f"/api/conversations/{conv_id}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True

    # Ensure conversation no longer exists
    get_res = client.get(f"/api/conversations/{conv_id}")
    assert get_res.status_code == 404


def test_clear_conversation_messages(client, app):
    """Test clearing conversation messages while preserving conversation record."""
    with app.app_context():
        c = ConversationService.create_conversation("Active Chat")
        conv_id = c.id
        ConversationService.add_message(conv_id, "user", "Message 1")
        ConversationService.add_message(conv_id, "assistant", "Response 1")

    res = client.post(f"/api/conversations/{conv_id}/clear")
    assert res.status_code == 200

    # Verify messages are cleared
    get_res = client.get(f"/api/conversations/{conv_id}")
    assert len(get_res.get_json()["conversation"]["messages"]) == 0
