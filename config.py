"""Configuration loader using environment variables."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"


def _get_moltbook_api_key() -> Optional[str]:
    """Moltbook API key from env or fallback to api_alone file."""
    key = os.getenv("MOLTBOOK_API_KEY")
    if key:
        return key.strip()
    # Fallback: read from api_alone file in project root (same as portfolio_os pattern for secrets)
    path = PROJECT_ROOT / "api_alone"
    if path.exists():
        try:
            return path.read_text().strip() or None
        except Exception:
            pass
    return None


class Config:
    """Application configuration."""

    # Moltbook API (agent identity)
    MOLTBOOK_API_KEY: Optional[str] = None

    # Agent persona: who the agent is and how it should behave on Moltbook
    # Set in .env as MOLTBOOK_AGENT_PERSONA (one line or use \n for newlines)
    # If learning is enabled and persona history exists, the latest learned persona overrides this.
    MOLTBOOK_AGENT_PERSONA: Optional[str] = os.getenv("MOLTBOOK_AGENT_PERSONA")

    # RL-style learning: maximize a metric by updating persona from experience
    # Set MOLTBOOK_METRIC_TO_MAXIMIZE to one of: upvotes_received, replies_received, follower_count, karma, engagement
    MOLTBOOK_METRIC_TO_MAXIMIZE: str = os.getenv("MOLTBOOK_METRIC_TO_MAXIMIZE", "engagement")
    MOLTBOOK_LEARNING_ENABLED: bool = os.getenv("MOLTBOOK_LEARNING_ENABLED", "true").lower() == "true"
    MOLTBOOK_CRITIC_UPDATE_AFTER_ACTIONS: int = int(os.getenv("MOLTBOOK_CRITIC_UPDATE_AFTER_ACTIONS", "5"))
    MOLTBOOK_ACTION_LOG_PATH: Optional[str] = os.getenv("MOLTBOOK_ACTION_LOG_PATH")
    MOLTBOOK_PERSONA_HISTORY_PATH: Optional[str] = os.getenv("MOLTBOOK_PERSONA_HISTORY_PATH")

    # AI model configuration (same names as portfolio_os for consistency)
    VISION_MODEL_API_KEY: Optional[str] = os.getenv("VISION_MODEL_API_KEY")
    VISION_MODEL_ENDPOINT: Optional[str] = os.getenv("VISION_MODEL_ENDPOINT")
    VISION_MODEL_DEPLOYMENT: Optional[str] = os.getenv("VISION_MODEL_DEPLOYMENT")
    VISION_MODEL_API_VERSION: Optional[str] = os.getenv(
        "VISION_MODEL_API_VERSION", "2024-02-15-preview"
    )
    AZURE_OPENAI_ENABLED: bool = (
        os.getenv("AZURE_OPENAI_ENABLED", "false").lower() == "true"
    )

    # Paths (data dir for action log and persona history)
    DATA_DIR = DATA_DIR


# Resolve MOLTBOOK_API_KEY once (env or api_alone file)
Config.MOLTBOOK_API_KEY = _get_moltbook_api_key()
