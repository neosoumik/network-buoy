import json
import logging
import os
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434") + "/api/generate"
MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:1b")

logger = logging.getLogger(__name__)


def generate(prompt: str, max_tokens: int = 256) -> str:
    payload = json.dumps(
        {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.9,
                "top_p": 0.95,
            },
        }
    ).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
            return str(body.get("response", "")).strip()
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        logger.warning("ollama unavailable (%s), using fallback", e)
        return ""
