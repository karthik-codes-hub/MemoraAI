"""
ContextAI - Real & Automated Five-Turn Memory Verification Script
Runs the mandatory 5-turn test to verify conversational retention and persistence.
Supports live OpenAI API testing as well as simulated local verification with --mock.
"""

import sys
import os
import argparse
from unittest.mock import MagicMock
from dotenv import load_dotenv

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

from app import create_app
from database import db
from models import Conversation, Message
from openai_service import OpenAIService


def run_five_turn_test(use_mock=False):
    print("=" * 65)
    print("ContextAI - Mandatory Five-Turn Conversational Memory Test")
    print("=" * 65)

    app = create_app()
    openai_svc = OpenAIService()

    is_configured = openai_svc.is_configured()
    if not is_configured and not use_mock:
        print("\n[!] Notice: OPENAI_API_KEY is not configured in .env.")
        print("To run against the LIVE OpenAI API:")
        print("  1. Add your real key in .env (OPENAI_API_KEY=sk-...)")
        print("  2. Run: python run_five_turn_test.py")
        print("\nTo run the automated verification with the built-in mock runner:")
        print("  Run: python run_five_turn_test.py --mock")
        print("Or run: python -m pytest tests/\n")
        return False

    client = app.test_client()

    if use_mock or not is_configured:
        print("\n[*] Running in MOCK VERIFICATION mode...")
        print("[*] Simulating OpenAI API responses with context inspection.\n")

        # Mocking OpenAI Chat Completion
        mock_client = MagicMock()

        def mock_completion(**kwargs):
            messages = kwargs.get("messages", [])
            resp = MagicMock()
            choice = MagicMock()

            # Check if this is turn 5
            last_msg = messages[-1]["content"] if messages else ""
            if "Based on our conversation" in last_msg:
                # Retrieve information directly from previous context messages
                full_history = " ".join(m.get("content", "") for m in messages)
                name = "Karthik" if "Karthik" in full_history else "Unknown"
                year = "third-year CSE student" if "third-year" in full_history or "CSE" in full_history else "Unknown"
                spec = "Artificial Intelligence and Machine Learning" if "Artificial Intelligence" in full_history else "Unknown"
                interest = "developing AI projects" if "AI projects" in full_history else "Unknown"

                choice.message.content = (
                    f"Based on our conversation:\n"
                    f"- **Name**: {name}\n"
                    f"- **Academic Year**: {year}\n"
                    f"- **Specialization**: {spec}\n"
                    f"- **Interest**: {interest}"
                )
            else:
                choice.message.content = f"I've noted that: \"{last_msg}\". How can I assist you further?"

            resp.choices = [choice]
            resp.usage.prompt_tokens = 45
            resp.usage.completion_tokens = 35
            resp.usage.total_tokens = 80
            return resp

        mock_client.chat.completions.create.side_effect = mock_completion
        app.config["OPENAI_API_KEY"] = "mock-key-for-test"

        # Patch OpenAIService._client
        import openai_service
        openai_service.OpenAIService.get_client = lambda self: mock_client

    else:
        print(f"\n[*] Target Model: {openai_svc.model}")
        print("[*] Connecting to live OpenAI Chat Completions API...\n")

    turns = [
        "My name is Karthik.",
        "I am a third-year CSE student.",
        "My specialization is Artificial Intelligence and Machine Learning.",
        "I am interested in developing AI projects.",
        "Based on our conversation, tell me my name, academic year, specialization, and interest.",
    ]

    conv_id = None

    for idx, prompt in enumerate(turns, 1):
        print(f"--- Turn {idx} ---")
        print(f"User: {prompt}")

        payload = {"message": prompt}
        if conv_id:
            payload["conversation_id"] = conv_id

        response = client.post("/api/chat", json=payload)
        if response.status_code != 200:
            print(f"[ERROR] API returned status {response.status_code}: {response.get_data(as_text=True)}")
            return False

        data = response.get_json()
        if not conv_id:
            conv_id = data["conversation_id"]
            print(f"[Conversation Created ID: {conv_id}]")

        assistant_reply = data["message"]["content"]
        print(f"AI: {assistant_reply}\n")

    # Step 6: Simulate browser refresh & query persistence
    print("--- Simulating Browser Refresh (SQLite Persistence Check) ---")
    print(f"Fetching conversation {conv_id} from SQLite database...")
    res = client.get(f"/api/conversations/{conv_id}")
    if res.status_code != 200:
        print("[ERROR] Failed to fetch refreshed conversation.")
        return False

    conv_data = res.get_json()["conversation"]
    messages = conv_data["messages"]
    print(f"[✓] Retrieved {len(messages)} messages successfully from SQLite database!")

    # Verify Turn 5 accuracy
    turn_5_answer = messages[-1]["content"].lower()
    checks = {
        "Name (Karthik)": "karthik" in turn_5_answer,
        "Academic Year (third-year)": "third" in turn_5_answer or "3rd" in turn_5_answer,
        "Specialization (AI / ML)": "artificial intelligence" in turn_5_answer or "ai" in turn_5_answer,
        "Interest (AI projects)": "project" in turn_5_answer or "developing" in turn_5_answer,
    }

    print("\n--- Verification Checklist ---")
    all_passed = True
    for item, passed in checks.items():
        symbol = "✓" if passed else "✗"
        print(f"[{symbol}] {item}: {'PASSED' if passed else 'NOT FOUND'}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n[SUCCESS] Mandatory Five-Turn Memory Test Passed Successfully!")
        print("The assistant maintained multi-turn context and accurately retrieved all 4 items.")
    else:
        print("\n[WARNING] Some specific keywords were not detected in Turn 5 response.")

    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ContextAI Five-Turn Memory Test")
    parser.add_argument("--mock", action="store_true", help="Run with mock responses without requiring live API key")
    args = parser.parse_args()

    success = run_five_turn_test(use_mock=args.mock)
    sys.exit(0 if success else 1)
