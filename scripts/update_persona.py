#!/usr/bin/env python3
"""
Run the critic: fetch engagement from Moltbook, compute the chosen metric,
and propose an updated persona. Append the new persona to history so the agent
uses it on the next run.

Usage:
  uv run python scripts/update_persona.py

Requires: MOLTBOOK_API_KEY (or api_alone), VISION_MODEL_API_KEY, and
MOLTBOOK_METRIC_TO_MAXIMIZE in .env (optional; default: engagement).
"""

import asyncio
import sys
from pathlib import Path

# Project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config
from experience import (
    append_persona_to_history,
    compute_metric,
    fetch_engagement,
    get_current_persona,
    load_action_log,
    run_critic,
    METRIC_OPTIONS,
)


def main() -> None:
    api_key = Config.MOLTBOOK_API_KEY
    if not api_key:
        print("Error: MOLTBOOK_API_KEY not set and api_alone not found.")
        sys.exit(1)
    metric_name = (Config.MOLTBOOK_METRIC_TO_MAXIMIZE or "engagement").strip().lower()
    if metric_name not in METRIC_OPTIONS:
        print(f"Warning: MOLTBOOK_METRIC_TO_MAXIMIZE must be one of {METRIC_OPTIONS}; using 'engagement'.")
        metric_name = "engagement"

    async def run() -> None:
        print("Fetching engagement from Moltbook...")
        engagement = await fetch_engagement(api_key)
        metric_value = compute_metric(engagement, metric_name)
        print(f"Engagement: karma={engagement.get('karma')}, followers={engagement.get('follower_count')}, "
              f"upvotes_received={engagement.get('upvotes_received')}, replies_received={engagement.get('replies_received')}")
        print(f"Metric '{metric_name}' = {metric_value}")

        actions = load_action_log()
        action_summary = "No actions logged yet."
        if actions:
            recent = actions[-20:]
            lines = [f"- {a['action_type']}: {a.get('details', {})}" for a in recent]
            action_summary = "\n".join(lines)

        current_persona = get_current_persona() or (Config.MOLTBOOK_AGENT_PERSONA or "").strip()
        if not current_persona:
            print("No current persona (no history and MOLTBOOK_AGENT_PERSONA not set). Set a seed persona in .env first.")
            sys.exit(1)

        print("Running critic to propose updated persona...")
        new_persona, critic_notes = await run_critic(
            current_persona=current_persona,
            engagement=engagement,
            metric_name=metric_name,
            metric_value=metric_value,
            action_summary=action_summary,
        )
        append_persona_to_history(
            persona=new_persona,
            metric_name=metric_name,
            metric_value=metric_value,
            critic_notes=critic_notes,
        )
        print("New persona appended to history. Next run of the agent will use it.")
        print("--- New persona ---")
        print(new_persona[:500] + ("..." if len(new_persona) > 500 else ""))

    asyncio.run(run())


if __name__ == "__main__":
    main()
