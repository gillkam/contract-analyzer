"""RAG Chat: LangChain + FAISS in-memory + Ollama"""
import os
import re
from io import BytesIO
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

_sessions: dict[str, "RAGChat"] = {}

# ── configurable via .env ──
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP"))
RAG_SIMILARITY_K = int(os.getenv("RAG_SIMILARITY_K"))


class RAGChat:
    def __init__(self, model: str, base_url: str):
        self.embeddings = OllamaEmbeddings(model=model, base_url=base_url)
        self.llm = Ollama(model=model, base_url=base_url, temperature=0)
        self.store = None

    def load_pdf(self, pdf_bytes: bytes) -> int:
        text = "\n".join(p.extract_text() or "" for p in PdfReader(BytesIO(pdf_bytes)).pages)
        chunks = RecursiveCharacterTextSplitter(
            chunk_size=RAG_CHUNK_SIZE, chunk_overlap=RAG_CHUNK_OVERLAP
        ).split_text(text)
        self.store = FAISS.from_texts(chunks, self.embeddings)
        return len(chunks)

    def chat(self, question: str) -> dict:
        if not self.store:
            return {"answer": "Upload a document first.", "context": []}
        docs = self.store.similarity_search(question, k=RAG_SIMILARITY_K)
        context = "\n\n".join(d.page_content for d in docs)
        answer = self.llm.invoke(f"Answer based ONLY on this context:\n\n{context}\n\nQuestion: {question}")
        # Strip <think>...</think> reasoning tags from deepseek-r1
        answer = re.sub(r"<think>.*?</think>\s*", "", answer, flags=re.DOTALL).strip()
        return {"answer": answer, "context": [d.page_content for d in docs[:3]]}

    def count(self) -> int:
        return len(self.store.docstore._dict) if self.store else 0


def get_rag_state(sid: str) -> RAGChat:
    if sid not in _sessions:
        _sessions[sid] = RAGChat(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)
    return _sessions[sid]