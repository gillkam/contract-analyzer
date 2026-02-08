
from typing import List
from langchain_core.documents import Document
import pdfplumber
from io import BytesIO


def load_docs_from_pdf_bytes(pdf_bytes: bytes) -> List[Document]:
    """Return page Documents + compact table-paragraph Documents.
    Each page text is one Document; each page's tables become one extra Document
    with rows joined by '; ' and cells joined by ' | '.
    """
    docs: List[Document] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            txt = page.extract_text() or ""
            if txt.strip():
                docs.append(Document(page_content=txt, metadata={"page": i, "type": "page"}))
            tables = page.extract_tables() or []
            if tables:
                rows = [" | ".join((c or "").strip() for c in row) for t in tables for row in t]
                para = "; ".join(r for r in rows if r)
                if para:
                    docs.append(Document(page_content=para, metadata={"page": i, "type": "table"}))
    return docs
