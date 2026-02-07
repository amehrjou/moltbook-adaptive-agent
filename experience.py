"""
RL-style experience and persona learning for the Moltbook agent.

- Actions (post, comment, upvote, follow) are logged.
- Engagement is fetched from Moltbook (profile + recent posts).
- A chosen metric is computed and a critic (LLM) proposes persona updates.
- Persona history is persisted so you can see how the persona evolved.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from config import Config
from moltbook_client import MoltbookClient


# Metric options: what to maximize. Set MOLTBOOK_METRIC_TO_MAXIMIZE in .env.
METRIC_OPTIONS = [
    "upvotes_received",   # Total upvotes on our posts (from recent posts)
    "replies_received",  # Total comments on our posts
    "follower_count",    # Current follower count (absolute)
    "karma",             # Moltbook karma from profile
    "engagement",        # upvotes_received + replies_received (combined)
]

DEFAULT_METRIC = "engagement"


def _data_dir() -> Path:
    return Path(Config.DATA_DIR)


def _action_log_path() -> Path:
    path = getattr(Config, "MOLTBOOK_ACTION_LOG_PATH", None)
    return Path(path) if path else _data_dir() / "action_log.jsonl"


def _persona_history_path() -> Path:
    path = getattr(Config, "MOLTBOOK_PERSONA_HISTORY_PATH", None)
    return Path(path) if path else _data_dir() / "persona_history.jsonl"


def _ensure_data_dir() -> None:
    _data_dir().mkdir(parents=True, exist_ok=True)


def log_action(action_type: str, details: dict[str, Any]) -> None:
    """Log an agent action (post, comment, upvote, follow, etc.) for experience tracking."""
    if not getattr(Config, "MOLTBOOK_LEARNING_ENABLED", True):
        return
    _ensure_data_dir()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "details": details,
    }
    with open(_action_log_path(), "a") as f:
        f.write(json.dumps(entry) + "\n")


def load_action_log() -> list[dict]:
    """Load all logged actions (for critic)."""
    path = _action_log_path()
    if not path.exists():
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


async def fetch_engagement(api_key: str) -> dict[str, Any]:
    """
    Fetch current engagement from Moltbook: profile (karma, followers) and recent posts' upvotes/replies.
    """
    async with MoltbookClient(api_key) as client:
        profile_resp = await client.get_agent_profile()
    # Handle both {"agent": ...} and direct profile
    agent = profile_resp.get("agent") or profile_resp
    if isinstance(agent, list):
        agent = agent[0] if agent else {}
    karma = agent.get("karma") or 0
    follower_count = agent.get("follower_count") or 0
    following_count = agent.get("following_count") or 0
    recent_posts = agent.get("recentPosts") or profile_resp.get("recentPosts") or []
    upvotes_received = 0
    replies_received = 0
    for p in recent_posts:
        if isinstance(p, dict):
            upvotes_received += p.get("upvotes") or p.get("score") or 0
            cc = p.get("comment_count")
            if cc is not None and isinstance(cc, (int, float)):
                replies_received += int(cc)
            elif isinstance(p.get("comments"), list):
                replies_received += len(p["comments"])
        elif isinstance(p, (list, tuple)) and len(p) > 1:
            # Some APIs return [id, title, upvotes, ...]
            if len(p) > 2:
                upvotes_received += int(p[2]) if str(p[2]).isdigit() else 0
    return {
        "karma": karma,
        "follower_count": follower_count,
        "following_count": following_count,
        "upvotes_received": upvotes_received,
        "replies_received": replies_received,
        "posts_count": len(recent_posts),
    }


def compute_metric(engagement: dict[str, Any], metric_name: str) -> float:
    """Compute the chosen metric from engagement dict."""
    name = (metric_name or DEFAULT_METRIC).strip().lower()
    if name == "karma":
        return float(engagement.get("karma") or 0)
    if name == "follower_count":
        return float(engagement.get("follower_count") or 0)
    if name == "upvotes_received":
        return float(engagement.get("upvotes_received") or 0)
    if name == "replies_received":
        return float(engagement.get("replies_received") or 0)
    if name == "engagement":
        return float(engagement.get("upvotes_received") or 0) + float(engagement.get("replies_received") or 0)
    return float(engagement.get("engagement", 0))


def get_current_persona() -> Optional[str]:
    """
    Get the current learned persona (last entry in history).
    If no history, returns None so caller can use MOLTBOOK_AGENT_PERSONA from config.
    """
    path = _persona_history_path()
    if not path.exists():
        return None
    last_line = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                last_line = line
    if not last_line:
        return None
    try:
        entry = json.loads(last_line)
        return entry.get("persona") or None
    except json.JSONDecodeError:
        return None


def load_persona_history() -> list[dict]:
    """Load full persona history (for inspection / replay)."""
    path = _persona_history_path()
    if not path.exists():
        return []
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def append_persona_to_history(
    persona: str,
    metric_name: str,
    metric_value: float,
    critic_notes: str = "",
) -> None:
    """Append a new persona entry to history (after critic run)."""
    _ensure_data_dir()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "persona": persona,
        "metric_name": metric_name,
        "metric_value": metric_value,
        "critic_notes": critic_notes,
    }
    with open(_persona_history_path(), "a") as f:
        f.write(json.dumps(entry) + "\n")


async def run_critic(
    current_persona: str,
    engagement: dict[str, Any],
    metric_name: str,
    metric_value: float,
    action_summary: str,
) -> tuple[str, str]:
    """
    Use the LLM (same model as agent) as critic: propose a new persona to improve the metric.
    Returns (new_persona_text, critic_notes).
    """
    from ai.base import get_default_model
    from pydantic_ai import Agent

    model = get_default_model()
    critic = Agent(
        model=model,
        system_prompt="You are a critic that improves Moltbook agent personas. Given the current persona, engagement stats, and the metric we want to maximize, output a revised persona (a few sentences or bullet points) that should improve that metric. Stay within Moltbook community norms. Output only the new persona text, no preamble.",
    )
    prompt = f"""Current persona:
{current_persona}

Engagement we observed:
- karma: {engagement.get('karma', 0)}
- follower_count: {engagement.get('follower_count', 0)}
- upvotes on our posts: {engagement.get('upvotes_received', 0)}
- replies on our posts: {engagement.get('replies_received', 0)}
- recent posts count: {engagement.get('posts_count', 0)}

Metric we want to maximize: {metric_name}
Current metric value: {metric_value}

Recent actions summary:
{action_summary}

Propose a revised persona that would likely improve {metric_name}. Output only the new persona text, no explanation."""
    result = await critic.run(prompt)
    new_persona = (result.output or "").strip()
    critic_notes = f"Metric: {metric_name}={metric_value}; critic proposed update."
    return new_persona or current_persona, critic_notes
