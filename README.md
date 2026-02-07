# Moltbook Agent

A Pydantic AI–powered agent that interacts with [Moltbook](https://www.moltbook.com)—the social network for AI agents—and can **learn from experience** by updating its own persona to improve a metric you choose.

---

## What it does

- **Talks to Moltbook**  
  Uses the [official Moltbook skill](https://www.moltbook.com/skill.md). You give natural-language instructions; the agent posts, comments, upvotes, searches, follows, and manages submolts via tools.

- **Persona-driven behavior**  
  You set a **persona** (identity, tone, topics). The agent uses it for every action so its style is consistent.

- **Learns from experience**  
  Actions are logged; engagement (upvotes, replies, followers, karma) is read from Moltbook; a **critic** (LLM) proposes an updated persona to improve a chosen metric. **Persona history** is saved so you can see how the agent’s “identity” evolves over time.

---

## Quick start

**Requirements:** Python 3.13+, [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/YOUR_USERNAME/moltbook-agent.git
cd moltbook-agent
uv sync
cp .env.example .env
# Edit .env: set MOLTBOOK_API_KEY and VISION_MODEL_API_KEY
uv run python main.py
```

In `.env` you need at least:

- `MOLTBOOK_API_KEY` – from [Moltbook](https://www.moltbook.com) (or put the key in a file named `api_alone`).
- `VISION_MODEL_API_KEY` – OpenAI (or Azure) key for the LLM.

Optional: `MOLTBOOK_AGENT_PERSONA` (seed persona) and `MOLTBOOK_METRIC_TO_MAXIMIZE` (what to improve). See [USAGE.md](USAGE.md) for details.

---

## Learning: adaptive persona from experience

The project includes an **experimental learning loop** that treats the agent’s persona as a **policy** that is updated from **reward** (a metric you choose), with a **critic** proposing the updates. In that sense it works like a lightweight, interpretable form of reinforcement learning: no gradients, but a clear loop of *act → measure → critique → update identity*.

### Why it’s interesting

In social environments, **identity and behavior co-evolve**: people (and agents) adjust how they present themselves based on feedback (likes, replies, follows). That’s hard to study in the wild. Here:

- **Actions** are explicit (post, comment, upvote, follow).
- **Reward** is a single metric you pick (engagement, karma, followers, etc.).
- **Policy** is the **persona** (free text), not neural weights.
- **Critic** is an LLM that proposes a new persona given the current one, recent actions, and observed reward.

So you get a **tractable loop**: the agent tries a persona → you measure outcomes → the critic suggests a new persona → you run again. The result is a **logged history of personas** over time: a record of how “who the agent is” changed as you optimized for different goals. That makes it useful both as a tool (improve engagement) and as a **small-scale model of identity plasticity** in a social, reward-shaped setting—something you can inspect, replay, and share (e.g. by anonymizing persona history for papers or blog posts).

### How to use it

1. Set a **seed persona** in `.env` (`MOLTBOOK_AGENT_PERSONA`) and a **metric** (`MOLTBOOK_METRIC_TO_MAXIMIZE`: e.g. `engagement`, `karma`, `follower_count`).
2. Run the agent: `uv run python main.py` — use Moltbook as usual. Actions are logged under `data/`.
3. Run the critic: `uv run python scripts/update_persona.py` — it fetches engagement, computes the metric, and appends a **new persona** to `data/persona_history.jsonl`.
4. Run the agent again; it uses the **latest persona** in history.
5. Inspect evolution: `uv run python scripts/show_persona_history.py` — prints the full persona history so you can see how the agent’s “self” changed.

Details, metric options, and config are in [USAGE.md](USAGE.md).

---

## Project layout

```
moltbook-agent/
├── agent.py           # Pydantic AI agent + Moltbook tools
├── config.py          # Config from env
├── experience.py      # Action log, engagement fetch, metric, persona history, critic
├── main.py            # Interactive entrypoint
├── moltbook_client.py # Moltbook API client
├── ai/
│   ├── base.py        # get_default_model(), create_agent()
│   └── __init__.py
├── scripts/
│   ├── update_persona.py      # Run critic, append new persona to history
│   └── show_persona_history.py # Print persona history
├── .env.example       # Safe template (no secrets)
├── pyproject.toml
├── README.md
└── USAGE.md           # Persona, commands, learning workflow
```

Secrets and local state stay out of the repo: `.env`, `api_alone`, `api_key_*`, and `data/` are gitignored.

---

## Moltbook and rate limits

- API base: `https://www.moltbook.com/api/v1` (see [skill](https://www.moltbook.com/skill.md)).
- Rate limits: 100 req/min; 1 post per 30 min; 1 comment per 20 s; 50 comments/day. The client returns structured errors on 429 instead of crashing.

---

## Security

Do not commit API keys. Use `.env` or the `api_alone` file and keep them out of version control (they are in `.gitignore`).

---

## License

Use and modify as you like. If you build on the learning loop or use the persona-history idea in research or writing, crediting the repo is appreciated.
