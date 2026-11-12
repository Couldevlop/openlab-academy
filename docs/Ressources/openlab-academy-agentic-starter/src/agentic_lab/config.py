import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    app_env: str
    max_steps: int
    verbose: bool
    model_provider: str
    ollama_base_url: str
    ollama_model: str


def load_settings() -> Settings:
    load_dotenv()
    try:
        max_steps = int(os.getenv("AGENT_MAX_STEPS", "5"))
    except ValueError as exc:
        raise ValueError("AGENT_MAX_STEPS doit être un entier.") from exc
    if not 1 <= max_steps <= 20:
        raise ValueError("AGENT_MAX_STEPS doit être compris entre 1 et 20.")
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        max_steps=max_steps,
        verbose=os.getenv("AGENT_VERBOSE", "true").lower() in {"1", "true", "yes"},
        model_provider=os.getenv("MODEL_PROVIDER", "demo").lower(),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
    )
