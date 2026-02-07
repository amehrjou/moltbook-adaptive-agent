#!/usr/bin/env python3
"""Print persona history so you can see how the persona changed over time."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from experience import _persona_history_path, load_persona_history


def main() -> None:
    path = _persona_history_path()
    if not path.exists():
        print("No persona history yet. Run the agent, then run scripts/update_persona.py to add entries.")
        return
    history = load_persona_history()
    if not history:
        print("Persona history is empty.")
        return
    print(f"Persona history ({len(history)} entries)\n")
    for i, entry in enumerate(history, 1):
        ts = entry.get("timestamp", "")[:19]
        metric = entry.get("metric_name", "")
        value = entry.get("metric_value", "")
        print(f"--- Entry {i} ({ts}) | {metric}={value} ---")
        print(entry.get("persona", "")[:400])
        if entry.get("critic_notes"):
            print(f"[Critic: {entry['critic_notes'][:100]}]")
        print()


if __name__ == "__main__":
    main()
