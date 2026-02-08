"""
Unit tests for backend/analyzer/utils_pdf.py

Covers:
  - load_docs_from_pdf_bytes() with a real minimal PDF
  - Edge cases: empty PDF, non-PDF bytes
"""

import pytest
from io import BytesIO


def _import_utils():
    from utils_pdf import load_docs_from_pdf_bytes
    return load_docs_from_pdf_bytes


class TestLoadDocsFromPdfBytes:
    def test_returns_documents(self, sample_pdf_bytes):
        load = _import_utils()
        docs = load(sample_pdf_bytes)
        assert isinstance(docs, list)
        # Should have at least 1 page document
        assert len(docs) >= 1

    def test_page_metadata(self, sample_pdf_bytes):
        load = _import_utils()
        docs = load(sample_pdf_bytes)
        page_docs = [d for d in docs if d.metadata.get("type") == "page"]
        for d in page_docs:
            assert "page" in d.metadata
            assert isinstance(d.metadata["page"], int)
            assert d.metadata["page"] >= 1

    def test_non_empty_content(self, sample_pdf_bytes):
        load = _import_utils()
        docs = load(sample_pdf_bytes)
        if docs:  # may be empty with hand-crafted PDF
            for d in docs:
                assert len(d.page_content.strip()) > 0

    def test_invalid_bytes_raises(self):
        load = _import_utils()
        with pytest.raises(Exception):
            load(b"this is not a pdf")

    def test_empty_bytes_raises(self):
        load = _import_utils()
        with pytest.raises(Exception):
            load(b"")

    def test_table_metadata_type(self, sample_pdf_bytes):
        """If tables are present, they should have type='table' metadata."""
        load = _import_utils()
        docs = load(sample_pdf_bytes)
        table_docs = [d for d in docs if d.metadata.get("type") == "table"]
        for d in table_docs:
            assert d.metadata["type"] == "table"
            assert "page" in d.metadata
