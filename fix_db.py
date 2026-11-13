"""
Database migration script for MemoraAI v2.0
Adds missing columns to existing database without losing data.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "contextai.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing tables
    tables = [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("Existing tables:", tables)

    # --- messages table: add attachments_json column if missing ---
    if "messages" in tables:
        msg_cols = [row[1] for row in cursor.execute("PRAGMA table_info(messages)").fetchall()]
        print("messages columns:", msg_cols)
        if "attachments_json" not in msg_cols:
            cursor.execute("ALTER TABLE messages ADD COLUMN attachments_json TEXT DEFAULT NULL")
            print("✅ Added attachments_json to messages table")
        else:
            print("✓  attachments_json already exists in messages")

    # --- Create uploaded_files table if missing ---
    if "uploaded_files" not in tables:
        cursor.execute("""
            CREATE TABLE uploaded_files (
                id VARCHAR(36) PRIMARY KEY,
                conversation_id VARCHAR(36) REFERENCES conversations(id) ON DELETE CASCADE,
                original_filename VARCHAR(255) NOT NULL,
                stored_filename VARCHAR(255) NOT NULL UNIQUE,
                mime_type VARCHAR(100) NOT NULL,
                file_size INTEGER NOT NULL,
                storage_path VARCHAR(500) NOT NULL,
                file_category VARCHAR(30) NOT NULL DEFAULT 'document',
                extracted_text TEXT,
                processing_status VARCHAR(30) NOT NULL DEFAULT 'completed',
                error_message TEXT,
                metadata_json TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Created uploaded_files table")
    else:
        print("✓  uploaded_files table already exists")

    # --- Create document_chunks table if missing ---
    if "document_chunks" not in tables:
        cursor.execute("""
            CREATE TABLE document_chunks (
                id VARCHAR(36) PRIMARY KEY,
                file_id VARCHAR(36) NOT NULL REFERENCES uploaded_files(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                page_number INTEGER,
                section_title VARCHAR(255),
                metadata_json TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON document_chunks(file_id)")
        print("✅ Created document_chunks table")
    else:
        print("✓  document_chunks table already exists")

    # Create index on uploaded_files.conversation_id if missing
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_conv_id ON uploaded_files(conversation_id)")

    conn.commit()
    conn.close()
    print("\n🎉 Database migration complete!")

if __name__ == "__main__":
    migrate()

