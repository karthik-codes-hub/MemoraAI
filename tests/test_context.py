from context_manager import ContextManager
from config import Config
from conversation_service import ConversationService


def test_token_estimation():
    """Verify tiktoken token estimation returns reasonable counts."""
    mgr = ContextManager()
    tokens = mgr.estimate_tokens("Hello, world! How are you today?")
    assert tokens > 0
    assert tokens < 20

    # Empty string should be 0
    assert mgr.estimate_tokens("") == 0


def test_message_token_calculation():
    """Verify message token estimation includes format overhead."""
    mgr = ContextManager()
    msg = {"role": "user", "content": "Tell me about quantum computing."}
    tokens = mgr.estimate_message_tokens(msg)
    # Content tokens + role tokens + 4 overhead
    assert tokens > 5


def test_context_building_with_system_and_summary():
    """Verify build_context_messages prepends system prompt and summary correctly."""
    mgr = ContextManager(max_context_tokens=2000, max_recent_messages=10)
    system_prompt = "You are ContextAI."
    summary = "User is Karthik, a third-year CSE student interested in AI."
    messages = [
        {"role": "user", "content": "What projects should I build?"},
    ]

    context = mgr.build_context_messages(system_prompt, messages, summary=summary)

    # 1st item: system prompt
    assert context[0]["role"] == "system"
    assert context[0]["content"] == system_prompt

    # 2nd item: summary note
    assert context[1]["role"] == "system"
    assert "Contextual Memory" in context[1]["content"]
    assert "Karthik" in context[1]["content"]

    # 3rd item: user message
    assert context[2]["role"] == "user"
    assert context[2]["content"] == "What projects should I build?"


def test_recent_message_truncation_under_budget():
    """Verify truncation preserves latest N messages and drops oldest when budget is tight."""
    # Configure tiny token budget
    mgr = ContextManager(
        max_context_tokens=150,
        reserved_response_tokens=50,
        max_recent_messages=5,
    )
    system_prompt = "Short prompt."
    messages = [
        {"role": "user", "content": f"Historical message number {i} with some extra padding text"}
        for i in range(10)
    ]

    context = mgr.build_context_messages(system_prompt, messages)

    # Must contain system prompt
    assert context[0]["role"] == "system"

    # Must only retain the newest messages that fit the budget
    assert len(context) < len(messages) + 1
    # The last message in context MUST be the most recent user message
    assert context[-1]["content"] == messages[-1]["content"]


def test_messages_to_summarize_partition():
    """Verify older messages are correctly identified for summarization while keeping recent intact."""
    mgr = ContextManager(summary_trigger_count=5)
    messages = [{"role": "user", "content": f"Turn {i}"} for i in range(10)]

    older = mgr.get_messages_to_summarize(messages, keep_recent=4)
    assert len(older) == 6
    assert older[0]["content"] == "Turn 0"
    assert older[-1]["content"] == "Turn 5"


def test_database_messages_preserved_after_truncation(app):
    """
    Critical requirement: Confirm that truncating the context for the API call
    does NOT delete or alter messages stored in the database.
    """
    with app.app_context():
        c = ConversationService.create_conversation("Preservation Test")
        for i in range(30):
            ConversationService.add_message(c.id, "user" if i % 2 == 0 else "assistant", f"Message {i}")

        db_messages = ConversationService.get_messages(c.id)
        assert len(db_messages) == 30

        # Run context manager truncation (max 5 messages)
        mgr = ContextManager(max_recent_messages=5)
        formatted = [{"role": m.role, "content": m.content} for m in db_messages]
        context = mgr.build_context_messages("System", formatted)

        # Truncated context has at most 1 system + 5 messages
        assert len(context) <= 6

        # Check DB again: all 30 messages must still exist in SQLite
        db_messages_after = ConversationService.get_messages(c.id)
        assert len(db_messages_after) == 30
