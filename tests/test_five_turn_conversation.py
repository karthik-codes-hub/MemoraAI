import pytest
from unittest.mock import MagicMock
from conversation_service import ConversationService
from context_manager import ContextManager
from config import Config


def test_mandatory_five_turn_conversation_flow(client, mock_openai, app):
    """
    Mandatory Five-Turn Conversation Test:
    Turn 1: "My name is Karthik."
    Turn 2: "I am a third-year CSE student."
    Turn 3: "My specialization is Artificial Intelligence and Machine Learning."
    Turn 4: "I am interested in developing AI projects."
    Turn 5: "Based on our conversation, tell me my name, academic year, specialization, and interest."
    """
    turns = [
        "My name is Karthik.",
        "I am a third-year CSE student.",
        "My specialization is Artificial Intelligence and Machine Learning.",
        "I am interested in developing AI projects.",
        "Based on our conversation, tell me my name, academic year, specialization, and interest.",
    ]

    conv_id = None

    # Custom mock response generator that inspects the context passed to verify memory retention
    context_calls = []

    def mock_chat_create(**kwargs):
        messages = kwargs.get("messages", [])
        context_calls.append(messages)
        mock_resp = MagicMock()
        mock_choice = MagicMock()

        # If it's turn 5, synthesize the contextual answer that retrieves all 4 facts
        if any("Based on our conversation, tell me my name" in m.get("content", "") for m in messages):
            mock_choice.message.content = (
                "Based on our conversation:\n"
                "- Name: Karthik\n"
                "- Academic Year: Third-year student\n"
                "- Specialization: Artificial Intelligence and Machine Learning\n"
                "- Interest: Developing AI projects"
            )
        else:
            mock_choice.message.content = f"Acknowledged turn: {messages[-1]['content']}"

        mock_resp.choices = [mock_choice]
        mock_resp.usage.prompt_tokens = 40
        mock_resp.usage.completion_tokens = 30
        mock_resp.usage.total_tokens = 70
        return mock_resp

    mock_openai.chat.completions.create.side_effect = mock_chat_create

    # Execute all 5 turns sequentially
    for idx, prompt in enumerate(turns):
        payload = {"message": prompt}
        if conv_id:
            payload["conversation_id"] = conv_id

        res = client.post("/api/chat", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True

        if idx == 0:
            conv_id = data["conversation_id"]
        else:
            assert data["conversation_id"] == conv_id

    # 1. Verify Turn 5 received full contextual memory
    last_call_messages = context_calls[-1]
    last_context_text = " ".join(m.get("content", "") for m in last_call_messages)
    assert "Karthik" in last_context_text
    assert "third-year" in last_context_text or "CSE" in last_context_text
    assert "Artificial Intelligence" in last_context_text
    assert "developing AI projects" in last_context_text

    # 2. Simulate browser refresh: fetch conversation details from /api/conversations/<id>
    refresh_res = client.get(f"/api/conversations/{conv_id}")
    assert refresh_res.status_code == 200
    conv_data = refresh_res.get_json()["conversation"]

    # Verify all 10 messages (5 user + 5 assistant) are persisted and ordered
    messages = conv_data["messages"]
    assert len(messages) == 10

    # Verify chronological sequence
    for i, prompt in enumerate(turns):
        user_msg = messages[i * 2]
        assistant_msg = messages[i * 2 + 1]
        assert user_msg["role"] == "user"
        assert user_msg["content"] == prompt
        assert assistant_msg["role"] == "assistant"

    # Verify Turn 5 assistant response contains all four requested items
    turn_5_response = messages[9]["content"]
    assert "Karthik" in turn_5_response
    assert "Third-year" in turn_5_response
    assert "Artificial Intelligence and Machine Learning" in turn_5_response
    assert "Developing AI projects" in turn_5_response
