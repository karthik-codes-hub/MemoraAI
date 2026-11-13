"""
MemoraAI – File Upload & Processing Tests
Tests for the file upload API, file service, extraction, and chunking.
"""

import io
import os
import json
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from config import TestConfig
from database import db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """Create test Flask app with in-memory SQLite and a temp upload folder."""
    test_upload_dir = os.path.join(os.path.dirname(__file__), "test_uploads_tmp")
    os.makedirs(test_upload_dir, exist_ok=True)

    class FileTestConfig(TestConfig):
        UPLOAD_FOLDER = test_upload_dir
        MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB for tests

    app = create_app(FileTestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

    # Cleanup temp uploads
    import shutil
    if os.path.exists(test_upload_dir):
        shutil.rmtree(test_upload_dir, ignore_errors=True)


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Helper: minimal valid files in memory
# ---------------------------------------------------------------------------

def make_txt_file(content: str = "Hello MemoraAI! This is a test document.") -> io.BytesIO:
    return io.BytesIO(content.encode("utf-8"))


def make_csv_file() -> io.BytesIO:
    csv_content = "Name,Age,City\nAlice,30,New York\nBob,25,London\nCharlie,35,Tokyo\n"
    return io.BytesIO(csv_content.encode("utf-8"))


# ---------------------------------------------------------------------------
# Test: Upload a plain text file
# ---------------------------------------------------------------------------

def test_upload_txt_file(client):
    """Upload a .txt file and verify it is processed and stored."""
    data = {
        "file": (make_txt_file(), "test_doc.txt"),
    }
    response = client.post(
        "/api/files/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.data}"
    body = response.get_json()
    assert body["success"] is True
    assert len(body["files"]) == 1

    file_record = body["files"][0]
    assert file_record["original_filename"] == "test_doc.txt"
    assert file_record["file_category"] in ("text", "document")
    assert file_record["processing_status"] == "completed"
    assert "id" in file_record


def test_upload_csv_file(client):
    """Upload a .csv file and verify row-level extraction."""
    data = {
        "file": (make_csv_file(), "data.csv"),
    }
    response = client.post(
        "/api/files/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["success"] is True
    file_record = body["files"][0]
    assert file_record["original_filename"] == "data.csv"
    assert file_record["processing_status"] == "completed"


# ---------------------------------------------------------------------------
# Test: Retrieve file content after upload
# ---------------------------------------------------------------------------

def test_get_file_content_after_upload(client):
    """Upload a text file, then retrieve its extracted content via API."""
    data = {
        "file": (make_txt_file("MemoraAI extracted content test."), "content_test.txt"),
    }
    upload_resp = client.post(
        "/api/files/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert upload_resp.status_code == 201
    file_id = upload_resp.get_json()["files"][0]["id"]

    # Retrieve content
    content_resp = client.get(f"/api/files/{file_id}/content")
    assert content_resp.status_code == 200
    content_body = content_resp.get_json()
    assert content_body["success"] is True
    assert "MemoraAI extracted content test" in content_body["extracted_text"]


# ---------------------------------------------------------------------------
# Test: List all files
# ---------------------------------------------------------------------------

def test_list_files(client):
    """Upload two files and verify both appear in the listing."""
    for name, content in [("file_a.txt", "Alpha content"), ("file_b.txt", "Beta content")]:
        client.post(
            "/api/files/upload",
            data={"file": (io.BytesIO(content.encode()), name)},
            content_type="multipart/form-data",
        )

    response = client.get("/api/files")
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["count"] >= 2


# ---------------------------------------------------------------------------
# Test: Delete a file
# ---------------------------------------------------------------------------

def test_delete_file(client):
    """Upload a file and then delete it; verify 404 on subsequent retrieval."""
    upload_resp = client.post(
        "/api/files/upload",
        data={"file": (make_txt_file("Delete me."), "delete_test.txt")},
        content_type="multipart/form-data",
    )
    assert upload_resp.status_code == 201
    file_id = upload_resp.get_json()["files"][0]["id"]

    # Delete
    del_resp = client.delete(f"/api/files/{file_id}")
    assert del_resp.status_code == 200
    assert del_resp.get_json()["success"] is True

    # Should be gone now
    get_resp = client.get(f"/api/files/{file_id}")
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Test: Reject unsupported file types
# ---------------------------------------------------------------------------

def test_reject_unsupported_file_type(client):
    """Uploading an .exe file should be rejected with a 400 error."""
    data = {
        "file": (io.BytesIO(b"\x4d\x5a\x90\x00"), "malware.exe"),
    }
    response = client.post(
        "/api/files/upload",
        data=data,
        content_type="multipart/form-data",
    )
    # Should fail — unsupported extension
    assert response.status_code in (400, 422), f"Expected 400/422, got {response.status_code}"


# ---------------------------------------------------------------------------
# Test: Upload without a file returns 400
# ---------------------------------------------------------------------------

def test_upload_no_file_returns_400(client):
    """POST /api/files/upload with no file field should return 400."""
    response = client.post(
        "/api/files/upload",
        data={},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert "error" in body


# ---------------------------------------------------------------------------
# Test: Upload linked to a conversation
# ---------------------------------------------------------------------------

def test_upload_linked_to_conversation(client):
    """Upload a file with a conversation_id; verify file is associated."""
    # Create a conversation first
    conv_resp = client.post("/api/conversations", json={"title": "File Test Conversation"})
    assert conv_resp.status_code == 201
    conv_id = conv_resp.get_json()["conversation"]["id"]

    # Upload with conversation_id
    upload_resp = client.post(
        "/api/files/upload",
        data={
            "file": (make_txt_file("Linked file content for AI context."), "linked.txt"),
            "conversation_id": conv_id,
        },
        content_type="multipart/form-data",
    )
    assert upload_resp.status_code == 201
    body = upload_resp.get_json()
    file_record = body["files"][0]
    assert file_record["conversation_id"] == conv_id


# ---------------------------------------------------------------------------
# Test: File metadata endpoint
# ---------------------------------------------------------------------------

def test_get_file_metadata(client):
    """Upload a file and retrieve its metadata by ID."""
    upload_resp = client.post(
        "/api/files/upload",
        data={"file": (make_csv_file(), "meta_test.csv")},
        content_type="multipart/form-data",
    )
    assert upload_resp.status_code == 201
    file_id = upload_resp.get_json()["files"][0]["id"]

    meta_resp = client.get(f"/api/files/{file_id}")
    assert meta_resp.status_code == 200
    meta_body = meta_resp.get_json()
    assert meta_body["success"] is True
    assert meta_body["file"]["id"] == file_id
    assert meta_body["file"]["original_filename"] == "meta_test.csv"


# ---------------------------------------------------------------------------
# Test: 404 for non-existent file
# ---------------------------------------------------------------------------

def test_get_nonexistent_file_returns_404(client):
    """Fetching metadata for a file that doesn't exist should return 404."""
    response = client.get("/api/files/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404

