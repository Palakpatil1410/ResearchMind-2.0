import os
import time
from typing import Any

from dotenv import load_dotenv
from groq import NotFoundError, RateLimitError
from langchain_groq import ChatGroq

load_dotenv(override=True)

MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv("GROQ_FALLBACK_MODELS", "llama-3.1-8b-instant").split(",")
    if m.strip() and m.strip() != MODEL_NAME
]


def build_llm(temperature: float = 0):
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add GROQ_API_KEY=your_key_here to your .env file."
        )
    primary = ChatGroq(model=MODEL_NAME, temperature=temperature, max_retries=1)
    if not FALLBACK_MODELS:
        return primary
    fallbacks = [
        ChatGroq(model=m, temperature=temperature, max_retries=1) for m in FALLBACK_MODELS
    ]
    return primary.with_fallbacks(
        fallbacks, exceptions_to_handle=(RateLimitError, NotFoundError)
    )

def safe_invoke(chain_or_agent: Any, inputs: dict, delay: float = 0.3):
    """Small throttle for Groq rate limits."""
    if delay > 0:
        time.sleep(delay)
    return chain_or_agent.invoke(inputs)