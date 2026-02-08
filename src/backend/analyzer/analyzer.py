# analyzer.py
import os
import re
from typing import Dict, List, Literal

import orjson
from json_repair import repair_json
from tenacity import retry, stop_after_attempt, wait_fixed
from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.retrievers import TFIDFRetriever

from prompts import (
    COMPLIANCE_QUESTIONS, QUESTION_KEYWORDS, COMPLIANCE_REQUIREMENTS,
    SINGLE_Q_SYSTEM, SINGLE_Q_USER,
)
from utils_pdf import load_docs_from_pdf_bytes
from ollama_client import OllamaClient

load_dotenv()

# ── Analyzer retrieval config (from .env) ──
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP"))
TOP_K_TEXT = int(os.getenv("TOP_K_TEXT"))
TOP_K_TABLE = int(os.getenv("TOP_K_TABLE"))


# ---------- Schema ----------
class ComplianceResult(BaseModel):
    compliance_question: str
    compliance_state: Literal["Fully Compliant", "Partially Compliant", "Non-Compliant"]
    confidence: int = Field(ge=0, le=100)
    relevant_quotes: List[str]
    rationale: str = Field(min_length=30)


ALLOWED_STATES = {"Fully Compliant", "Partially Compliant", "Non-Compliant"}


# ---------- Retrieval ----------
def _pick_context_chunks(docs: List[Document], query_terms: List[str], top_k: int = 10) -> List[str]:
    """
    Split documents, TF-IDF rank by query_terms, return top_k chunk texts.
    Chunk size/overlap are read from .env (CHUNK_SIZE / CHUNK_OVERLAP).
    """
    if not docs:
        return []
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.split_documents(docs)
    if not chunks:
        return []
    retriever = TFIDFRetriever.from_documents(chunks)
    retriever.k = top_k
    query = " ".join(query_terms)
    results = retriever.invoke(query)
    return [d.page_content for d in results]


# ---------- Policy mapping (no quote grounding) ----------
def _apply_policy(state: str, confidence: int) -> tuple[str, int]:
    """
    Enforce deterministic thresholds aligned with the prompt rules:
      <40    => Non-Compliant
      40–84  => Partially Compliant
      >=85   => Fully Compliant (or keep if valid)
    """
    confidence = max(0, min(int(confidence), 98))
    if confidence < 40:
        return "Non-Compliant", confidence
    if confidence < 85:
        return "Partially Compliant", confidence
    if state not in ALLOWED_STATES:
        return "Fully Compliant", confidence
    return state, confidence


# ---------- JSON parsing (robust) ----------
def _strip_wrappers(raw: str) -> str:
    """
    Remove <think>...</think> and stray code fences, then trim.
    """
    if not raw:
        return raw
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    raw = re.sub(r"```(?:json)?", "", raw)
    raw = re.sub(r"```", "", raw)
    return raw.strip()


@retry(stop=stop_after_attempt(3), wait=wait_fixed(0.2))
def _parse_llm_json(raw: str) -> dict:
    """
    1) Strip wrappers
    2) Extract first {...} block
    3) Repair with json-repair
    4) Parse with orjson
    Retries once on failure via tenacity.
    """
    cleaned = _strip_wrappers(raw)
    m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in LLM response.")
    repaired = repair_json(m.group(0))
    return orjson.loads(repaired)


# ---------- Per-question analysis ----------
def _analyze_single_question(client: OllamaClient, question: str, context: str) -> dict:
    requirement = COMPLIANCE_REQUIREMENTS.get(question, question)
    if not context.strip():
        return {
            "compliance_question": question,
            "compliance_state": "Non-Compliant",
            "confidence": 0,
            "relevant_quotes": [],
            "rationale": "No relevant evidence found in extracted context.",
        }

    user_prompt = SINGLE_Q_USER.format(context=context, requirement=requirement)

    try:
        raw = client.complete_json(system=SINGLE_Q_SYSTEM, user=user_prompt).strip()
        data = _parse_llm_json(raw)

        # Extract fields (no grounding)
        state = data.get("compliance_state") or "Partially Compliant"

        conf_raw = data.get("confidence", 60)
        if isinstance(conf_raw, (int, float)):
            conf = int(conf_raw)
        else:
            # Accept "71.4%" or "(5/7)*100 = 71.4" forms
            nums = re.findall(r"[\d.]+", str(conf_raw))
            conf = int(float(nums[-1])) if nums else 60

        quotes = data.get("relevant_quotes", []) or []
        if isinstance(quotes, str):
            quotes = [quotes]
        # Normalize quotes (handle dicts) and strip <think> tags
        normalised: list[str] = []
        for q in quotes:
            if isinstance(q, dict):
                txt = q.get("text") or q.get("quote") or ""
                sec = q.get("section", "")
                val = f"Section {sec}: {txt}".strip(": ") if sec else str(txt) or str(q)
            else:
                val = str(q)
            val = re.sub(r"<think>.*?</think>\s*", "", val, flags=re.DOTALL).strip()
            if val:
                normalised.append(val)
        quotes = normalised

        rationale = data.get("rationale") or ""
        if isinstance(rationale, list):
            rationale = " ".join(str(r) for r in rationale)
        rationale = re.sub(r"<think>.*?</think>\s*", "", str(rationale), flags=re.DOTALL).strip()
        if not rationale:
            rationale = (
                "Decision based on the provided context; the explanation from the model was short, "
                "so a concise rationale has been supplied."
            )

        # Apply unbiased policy thresholds (no quote checks)
        state, conf = _apply_policy(state, conf)

        result = {
            "compliance_question": question,
            "compliance_state": state,
            "confidence": conf,
            "relevant_quotes": quotes,
            "rationale": rationale,
        }
        return ComplianceResult(**result).model_dump()

    except (ValidationError, Exception) as e:
        return {
            "compliance_question": question,
            "compliance_state": "Non-Compliant",
            "confidence": 0,
            "relevant_quotes": [],
            "rationale": f"Error analyzing: {str(e)[:200]}",
        }


# ---------- Public entrypoint ----------
def analyze_pdf_bytes(pdf_bytes: bytes, model: str) -> List[Dict]:
    """
    Extract text + table rows, retrieve relevant chunks for each question,
    call LLM once per question, parse robustly, and apply the threshold policy.
    """
    docs = load_docs_from_pdf_bytes(pdf_bytes)  # includes page text + table rows
    table_docs = [d for d in docs if d.metadata.get("type") == "table"]

    client = OllamaClient(model=model)
    results: List[Dict] = []

    for q in COMPLIANCE_QUESTIONS:
        terms = QUESTION_KEYWORDS.get(q, [q])

        text_chunks = _pick_context_chunks(docs, terms, top_k=TOP_K_TEXT)
        table_chunks = _pick_context_chunks(table_docs, terms, top_k=TOP_K_TABLE) if table_docs else []

        # Deduplicate: remove table chunks already present in text chunks
        seen = set(text_chunks)
        unique_table = [t for t in table_chunks if t not in seen]
        all_chunks = text_chunks + unique_table

        ctx = "\n\n".join(all_chunks) if all_chunks else ""
        results.append(_analyze_single_question(client, q, ctx))

    return results