
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ── LLM generation options (from .env) ──
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE"))
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT"))
OLLAMA_SEED = int(os.getenv("OLLAMA_SEED"))


class OllamaClient:
    def __init__(self, model: str, base_url: str = None, timeout: int = None):
        self.model = model
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL")
        self.timeout = timeout or int(os.getenv("OLLAMA_TIMEOUT"))

    def complete_json(self, system: str, user: str) -> str:
        # NOTE: format:"json" is NOT used because deepseek-r1 needs its
        # <think> reasoning chain to produce accurate scores.  The analyzer
        # strips <think> wrappers and extracts the JSON object via regex,
        # so the final output to the caller IS valid JSON.
        payload = {
            "model": self.model,
            "stream": False,
            "options": {
                "temperature": OLLAMA_TEMPERATURE,
                "top_p": OLLAMA_TOP_P,
                "num_predict": OLLAMA_NUM_PREDICT,
                "seed": OLLAMA_SEED
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        }
        r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")
