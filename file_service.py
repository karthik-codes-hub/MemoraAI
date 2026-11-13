import os
import csv
import io
import json
import uuid
import base64
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from werkzeug.utils import secure_filename
from PIL import Image

# Import extraction libraries
import pypdf
import docx
import pptx
import openpyxl

from config import Config
from database import db
from models import UploadedFile, DocumentChunk

logger = logging.getLogger(__name__)


class FileProcessingError(Exception):
    """Custom exception for file upload and extraction errors."""
    pass


class FileService:
    """Service for handling file uploads, validation, document text extraction, and chunking."""

    @staticmethod
    def get_file_category(extension: str) -> str:
        """Categorize file format into document, spreadsheet, presentation, image, or text."""
        ext = extension.lower().lstrip(".")
        if ext in ("pdf", "docx"):
            return "document"
        elif ext in ("csv", "xlsx"):
            return "spreadsheet"
        elif ext in ("pptx",):
            return "presentation"
        elif ext in ("png", "jpg", "jpeg", "webp"):
            return "image"
        elif ext in ("txt", "md"):
            return "text"
        return "other"

    @staticmethod
    def validate_file(filename: str, file_size: int) -> Tuple[bool, str]:
        """Validate file extension and size constraints."""
        if not filename or "." not in filename:
            return False, "File must have a valid extension."

        ext = filename.rsplit(".", 1)[1].lower()
        if ext not in Config.ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(Config.ALLOWED_EXTENSIONS))
            return False, f"Unsupported file type .{ext}. Supported formats: {allowed}"

        if file_size > Config.MAX_CONTENT_LENGTH:
            max_mb = Config.MAX_CONTENT_LENGTH // (1024 * 1024)
            return False, f"File size exceeds the {max_mb}MB limit."

        return True, ""

    @classmethod
    def save_and_process_file(
        cls, file_storage, conversation_id: Optional[str] = None
    ) -> UploadedFile:
        """
        Saves incoming Werkzeug FileStorage object to disk, extracts its text/data,
        creates document chunks, and commits the UploadedFile model to database.
        """
        original_name = file_storage.filename or "uploaded_file"
        safe_name = secure_filename(original_name) or "file"
        ext = original_name.rsplit(".", 1)[1].lower() if "." in original_name else ""

        # Read file bytes into memory to compute size and inspect
        file_bytes = file_storage.read()
        file_size = len(file_bytes)

        # Validate
        valid, err = cls.validate_file(original_name, file_size)
        if not valid:
            raise FileProcessingError(err)

        if file_size == 0:
            raise FileProcessingError("The uploaded file is empty.")

        # Create unique stored filename
        unique_prefix = uuid.uuid4().hex[:12]
        stored_filename = f"{unique_prefix}_{safe_name}"
        storage_path = str(Config.UPLOAD_FOLDER / stored_filename)

        # Write to disk
        try:
            with open(storage_path, "wb") as f:
                f.write(file_bytes)
        except Exception as e:
            logger.error(f"Failed to write file to disk: {e}")
            raise FileProcessingError("Could not store file on server.")

        category = cls.get_file_category(ext)
        mime_type = file_storage.content_type or f"application/{ext}"

        # Initialize UploadedFile record
        uploaded_file = UploadedFile(
            conversation_id=conversation_id,
            original_filename=original_name,
            stored_filename=stored_filename,
            mime_type=mime_type,
            file_size=file_size,
            storage_path=storage_path,
            file_category=category,
            processing_status="processing",
        )
        db.session.add(uploaded_file)
        db.session.commit()

        # Extract content based on category/format
        extracted_text = ""
        metadata: Dict[str, Any] = {}
        chunks_data: List[Dict[str, Any]] = []

        try:
            if ext == "pdf":
                extracted_text, metadata, chunks_data = cls._extract_pdf(storage_path)
            elif ext == "docx":
                extracted_text, metadata, chunks_data = cls._extract_docx(storage_path)
            elif ext in ("txt", "md"):
                extracted_text, metadata, chunks_data = cls._extract_text(storage_path)
            elif ext == "csv":
                extracted_text, metadata, chunks_data = cls._extract_csv(storage_path)
            elif ext == "xlsx":
                extracted_text, metadata, chunks_data = cls._extract_xlsx(storage_path)
            elif ext == "pptx":
                extracted_text, metadata, chunks_data = cls._extract_pptx(storage_path)
            elif category == "image":
                extracted_text, metadata, chunks_data = cls._process_image(storage_path, mime_type)

            uploaded_file.extracted_text = extracted_text
            uploaded_file.metadata_json = json.dumps(metadata)
            uploaded_file.processing_status = "completed"

            # Create DocumentChunk records
            for idx, ch in enumerate(chunks_data):
                chunk = DocumentChunk(
                    file_id=uploaded_file.id,
                    chunk_index=idx,
                    content=ch.get("content", ""),
                    page_number=ch.get("page_number"),
                    section_title=ch.get("section_title"),
                    metadata_json=json.dumps(ch.get("metadata", {})),
                )
                db.session.add(chunk)

            db.session.commit()
            logger.info(f"Successfully processed {original_name} ({len(chunks_data)} chunks)")
            return uploaded_file

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error extracting content from {original_name}: {e}", exc_info=True)
            uploaded_file.processing_status = "failed"
            uploaded_file.error_message = str(e)
            db.session.commit()
            raise FileProcessingError(f"Extraction failed: {str(e)}")

    @classmethod
    def _extract_pdf(cls, file_path: str) -> Tuple[str, Dict, List[Dict]]:
        """Extract text page by page from PDF files using pypdf."""
        reader = pypdf.PdfReader(file_path)
        total_pages = len(reader.pages)
        full_text_list = []
        chunks = []

        for page_idx, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                page_header = f"--- [Page {page_idx} of {total_pages}] ---"
                full_text_list.append(f"{page_header}\n{text}")

                # Create page chunk or sub-chunks if very long
                sub_chunks = cls._chunk_text(text, max_chars=Config.CHUNK_SIZE, overlap=Config.CHUNK_OVERLAP)
                for sc in sub_chunks:
                    chunks.append({
                        "content": sc,
                        "page_number": page_idx,
                        "section_title": f"Page {page_idx}",
                    })

        full_extracted = "\n\n".join(full_text_list)
        if not full_extracted.strip():
            full_extracted = "[Notice: This PDF does not contain extractable text layers, e.g. scanned image]."

        metadata = {"page_count": total_pages, "has_text": bool(chunks)}
        return full_extracted, metadata, chunks

    @classmethod
    def _extract_docx(cls, file_path: str) -> Tuple[str, Dict, List[Dict]]:
        """Extract paragraphs and tables from Word (.docx) documents."""
        doc = docx.Document(file_path)
        text_lines = []
        chunks = []

        for p in doc.paragraphs:
            val = p.text.strip()
            if val:
                text_lines.append(val)

        for table in doc.tables:
            table_rows = []
            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                table_rows.append(" | ".join(cells))
            if table_rows:
                text_lines.append("[Table Data]:\n" + "\n".join(table_rows))

        full_extracted = "\n\n".join(text_lines)
        sub_chunks = cls._chunk_text(full_extracted, max_chars=Config.CHUNK_SIZE, overlap=Config.CHUNK_OVERLAP)
        for idx, sc in enumerate(sub_chunks):
            chunks.append({
                "content": sc,
                "section_title": f"Section {idx + 1}",
            })

        metadata = {"paragraph_count": len(doc.paragraphs), "table_count": len(doc.tables)}
        return full_extracted, metadata, chunks

    @classmethod
    def _extract_text(cls, file_path: str) -> Tuple[str, Dict, List[Dict]]:
        """Extract plain text or Markdown files with fallback encoding."""
        content = ""
        for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        sub_chunks = cls._chunk_text(content, max_chars=Config.CHUNK_SIZE, overlap=Config.CHUNK_OVERLAP)
        chunks = [{"content": sc, "section_title": f"Part {i+1}"} for i, sc in enumerate(sub_chunks)]
        metadata = {"char_count": len(content), "line_count": len(content.splitlines())}
        return content, metadata, chunks

    @classmethod
    def _extract_csv(cls, file_path: str) -> Tuple[str, Dict, List[Dict]]:
        """Extract and format tabular CSV data."""
        lines = []
        row_count = 0
        headers = []

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader):
                if idx == 0:
                    headers = row
                    lines.append("| " + " | ".join(headers) + " |")
                    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                else:
                    lines.append("| " + " | ".join(row) + " |")
                row_count += 1
                if row_count > 1000:  # Truncate preview to first 1000 rows
                    lines.append(f"... [Truncated after 1000 rows. Total rows parsed: {row_count}]")
                    break

        full_extracted = "\n".join(lines)
        sub_chunks = cls._chunk_text(full_extracted, max_chars=Config.CHUNK_SIZE, overlap=Config.CHUNK_OVERLAP)
        chunks = [{"content": sc, "section_title": f"Rows Batch {i+1}"} for i, sc in enumerate(sub_chunks)]
        metadata = {"headers": headers, "row_count": row_count}
        return full_extracted, metadata, chunks

    @classmethod
    def _extract_xlsx(cls, file_path: str) -> Tuple[str, Dict, List[Dict]]:
        """Extract sheets and data from Excel spreadsheets."""
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet_summaries = []
        chunks = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            sheet_lines = [f"### Sheet: {sheet_name}"]
            max_r = min(ws.max_row or 0, 500)
            max_c = min(ws.max_column or 0, 50)

            rows_data = []
            for r in range(1, max_r + 1):
                row_vals = [
                    str(ws.cell(row=r, column=c).value or "").replace("\n", " ").strip()
                    for c in range(1, max_c + 1)
                ]
                # Filter empty rows
                if any(row_vals):
                    rows_data.append(" | ".join(row_vals))

            if rows_data:
                sheet_lines.append("\n".join(rows_data[:200]))  # sample first 200 rows
                if len(rows_data) > 200:
                    sheet_lines.append(f"... [Total populated rows in sheet: {len(rows_data)}]")

            sheet_text = "\n".join(sheet_lines)
            sheet_summaries.append(sheet_text)

            chunks.append({
                "content": sheet_text[:Config.CHUNK_SIZE],
                "section_title": f"Sheet: {sheet_name}",
            })

        full_extracted = "\n\n".join(sheet_summaries)
        metadata = {"sheets": wb.sheetnames, "sheet_count": len(wb.sheetnames)}
        return full_extracted, metadata, chunks

    @classmethod
    def _extract_pptx(cls, file_path: str) -> Tuple[str, Dict, List[Dict]]:
        """Extract slide titles and bullet points from PowerPoint presentations."""
        prs = pptx.Presentation(file_path)
        slides_text = []
        chunks = []

        for slide_idx, slide in enumerate(prs.slides, start=1):
            slide_lines = [f"--- [Slide {slide_idx}] ---"]
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        txt = paragraph.text.strip()
                        if txt:
                            slide_lines.append(txt)

            slide_content = "\n".join(slide_lines)
            slides_text.append(slide_content)
            chunks.append({
                "content": slide_content,
                "page_number": slide_idx,
                "section_title": f"Slide {slide_idx}",
            })

        full_extracted = "\n\n".join(slides_text)
        metadata = {"slide_count": len(prs.slides)}
        return full_extracted, metadata, chunks

    @classmethod
    def _process_image(cls, file_path: str, mime_type: str) -> Tuple[str, Dict, List[Dict]]:
        """Validate image, record dimensions, and read base64 data for multimodal AI."""
        with Image.open(file_path) as img:
            width, height = img.size
            format_name = img.format

        with open(file_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")

        extracted_text = (
            f"[Attached Image: {os.path.basename(file_path)} | Format: {format_name} | "
            f"Resolution: {width}x{height}px | MIME: {mime_type}]"
        )
        metadata = {
            "width": width,
            "height": height,
            "format": format_name,
            "base64_preview": b64_data[:80] + "...",
            "base64_full": b64_data,
        }
        chunks = [{"content": extracted_text, "section_title": "Image Metadata"}]
        return extracted_text, metadata, chunks

    @classmethod
    def _chunk_text(cls, text: str, max_chars: int = 1500, overlap: int = 200) -> List[str]:
        """Split long document text into overlapping chunks without breaking sentences where possible."""
        if not text:
            return []
        if len(text) <= max_chars:
            return [text]

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + max_chars
            if end >= text_len:
                chunks.append(text[start:].strip())
                break

            # Find convenient break point (paragraph or sentence)
            breakpoint = text.rfind("\n\n", start, end)
            if breakpoint == -1 or breakpoint <= start:
                breakpoint = text.rfind(". ", start, end)
            if breakpoint == -1 or breakpoint <= start:
                breakpoint = end

            chunk = text[start:breakpoint].strip()
            if chunk:
                chunks.append(chunk)

            start = max(start + 1, breakpoint - overlap)

        return chunks

    @staticmethod
    def get_file(file_id: str) -> Optional[UploadedFile]:
        """Retrieve UploadedFile record by ID."""
        return UploadedFile.query.filter_by(id=file_id).first()

    @staticmethod
    def get_conversation_files(conversation_id: str) -> List[UploadedFile]:
        """Retrieve all files associated with a conversation."""
        return (
            UploadedFile.query.filter_by(conversation_id=conversation_id)
            .order_by(UploadedFile.created_at.desc())
            .all()
        )

    @staticmethod
    def get_all_files(search_query: Optional[str] = None, category: Optional[str] = None) -> List[UploadedFile]:
        """Retrieve all uploaded files with optional search and category filters."""
        query = UploadedFile.query
        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            query = query.filter(UploadedFile.original_filename.ilike(term))
        if category and category.strip() and category != "all":
            query = query.filter_by(file_category=category.strip().lower())

        return query.order_by(UploadedFile.created_at.desc()).all()

    @staticmethod
    def delete_file(file_id: str) -> bool:
        """Delete an uploaded file record, its chunks, and its underlying disk storage."""
        file_rec = UploadedFile.query.filter_by(id=file_id).first()
        if not file_rec:
            return False

        # Remove from disk if file exists
        if file_rec.storage_path and os.path.exists(file_rec.storage_path):
            try:
                os.remove(file_rec.storage_path)
            except Exception as e:
                logger.warning(f"Could not remove disk file {file_rec.storage_path}: {e}")

        db.session.delete(file_rec)
        db.session.commit()
        return True

    @staticmethod
    def get_file_content_context(file_ids: List[str], max_chars: int = 12000) -> str:
        """
        Builds a structured contextual string representing the contents of attached files
        to inject into the conversational prompt for the LLM.
        """
        if not file_ids:
            return ""

        context_sections = []
        total_chars = 0

        for fid in file_ids:
            file_rec = UploadedFile.query.filter_by(id=fid).first()
            if not file_rec or not file_rec.extracted_text:
                continue

            header = (
                f"=== ATTACHED FILE: {file_rec.original_filename} "
                f"({file_rec.file_category.upper()}, {file_rec.file_size // 1024} KB) ==="
            )

            # Available characters for this document
            remaining = max(500, max_chars - total_chars)
            doc_text = file_rec.extracted_text[:remaining]
            if len(file_rec.extracted_text) > remaining:
                doc_text += f"\n... [Additional document content truncated to fit context budget] ..."

            section = f"{header}\n{doc_text}\n{'=' * len(header)}"
            context_sections.append(section)
            total_chars += len(section)

            if total_chars >= max_chars:
                break

        return "\n\n".join(context_sections)

