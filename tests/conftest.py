import pytest
from unittest.mock import MagicMock
from app import create_app
from config import TestConfig
from database import db


@pytest.fixture
def app():
    """Create and configure a test Flask application instance."""
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client for HTTP requests."""
    return app.test_client()


@pytest.fixture
def mock_openai(monkeypatch):
    """
    Mock OpenAI client responses for fast, deterministic, zero-cost unit testing.
    """
    mock_client = MagicMock()

    # Default completion mock
    mock_choice = MagicMock()
    mock_choice.message.content = "I remember our previous discussion. Your name is Karthik and you study CSE."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 50
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 70

    mock_client.chat.completions.create.return_value = mock_response

    # Patch OpenAI constructor in openai_service
    monkeypatch.setattr("openai_service.OpenAI", lambda api_key: mock_client)

    return mock_client
