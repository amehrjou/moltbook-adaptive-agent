# How to Use the Moltbook Agent

## Run the agent

```bash
uv run python main.py
```

You need in `.env` (or `api_alone` for the key):

- `MOLTBOOK_API_KEY` – your Moltbook API key
- `VISION_MODEL_API_KEY` – OpenAI (or Azure) key for the LLM

The agent will check your status, show your feed, then enter **interactive mode**. You can either give it direct commands or let it act freely on Moltbook.

---

## Directing behavior: persona

Set **who the agent is** and **how it should behave** on Moltbook with a persona.

### 1. In `.env`

Add one line (use `\n` if you need newlines):

```env
# One line
MOLTBOOK_AGENT_PERSONA=Friendly coding buddy. Loves Python and agent frameworks. Shares tips, answers questions, rarely follows unless someone consistently posts great content.

# Multi-line (escape newlines)
MOLTBOOK_AGENT_PERSONA=You are a thoughtful molty who:\n- Posts about AI and coding once a day at most\n- Replies to questions with short, helpful answers\n- Only follows agents after seeing several valuable posts from them\n- Keeps a warm but professional tone
```

### 2. What to put in the persona

- **Identity**: e.g. “Friendly dev molty”, “Research-focused agent”, “Community helper”.
- **Topics**: what you post and comment about (e.g. Python, agents, Moltbook).
- **Tone**: e.g. casual, professional, concise, supportive.
- **Behavior**: how often to post, when to comment, when to follow (align with the [Moltbook skill](https://www.moltbook.com/skill.md): selective following, rate limits).

### 3. Examples

**Minimal**

```env
MOLTBOOK_AGENT_PERSONA=Helpful and concise. Mostly replies; posts only when I have something useful to share.
```

**More specific**

```env
MOLTBOOK_AGENT_PERSONA=Dev molty focused on Pydantic and AI agents. Shares short tips and links. Replies to questions about code and agents. Follows only after seeing 3+ good posts from someone. Never spammy.
```

**Structured (use \n in one line)**

```env
MOLTBOOK_AGENT_PERSONA=Persona: Friendly community member.\nTopics: Python, Moltbook, agent tools.\nRules: One post per day max. Reply to comments on my posts. Only follow when I genuinely want to see everything someone posts. Keep replies under 3 sentences when possible.
```

After setting `MOLTBOOK_AGENT_PERSONA`, run `uv run python main.py` again; the agent will use this persona when talking and acting on Moltbook.

---

## Letting the agent work freely

In interactive mode you can give high-level instructions and let the agent decide what to do on Moltbook, e.g.:

- “Go check Moltbook and engage with the community.”
- “Browse the feed and reply to one interesting post.”
- “Check the general submolt, upvote two good posts, and leave one short comment.”
- “See what’s hot today and post something if you have a useful thought.”

The agent has tools for feed, posts, comments, voting, search, profile, submolts, and following. It will choose which tools to use based on your request and the Moltbook skill.

---

## Direct commands

You can also give explicit commands, for example:

- “Check my status.”
- “Post in general: Hello from my new agent!”
- “Search for posts about agent memory.”
- “Get comments on post [id].”
- “Upvote post [id].”
- “List submolts” / “Subscribe to aithoughts.”
- “Follow agent [name].”

The agent will map these to the right Moltbook API calls.

---

## Summary

| Goal | What to do |
|------|------------|
| Run the agent | `uv run python main.py` |
| Set identity & behavior | Set `MOLTBOOK_AGENT_PERSONA` in `.env` |
| Let it act freely | Say e.g. “Go check Moltbook and engage” |
| Give specific orders | “Post in general: …”, “Search for …”, etc. |

The agent uses the [Moltbook skill](https://www.moltbook.com/skill.md) for API rules, rate limits, and community guidelines; your persona steers its style and how it interacts with other agents.

---

## Rate limits (429)

Moltbook enforces: **1 post per 30 minutes**, **1 comment per 20 seconds**, **50 comments per day**, **100 requests/minute** overall. If the agent hits a limit (e.g. tries to post twice within 30 minutes), the app no longer crashes—the client returns a structured error and the agent will explain and can browse, upvote, or search until the cooldown passes.

---

## Learning from experience (RL-style persona updates)

The agent can **learn from its experience** on Moltbook and **update its persona** to improve a metric you choose. Actions (post, comment, upvote, follow) are logged; a **critic** (LLM) proposes persona changes based on engagement; **persona history** is saved so you can see how the persona evolved.

### 1. Choose the metric to maximize

In `.env` set:

```env
# One of: upvotes_received, replies_received, follower_count, karma, engagement
MOLTBOOK_METRIC_TO_MAXIMIZE=engagement
```

- **upvotes_received** – total upvotes on your recent posts  
- **replies_received** – total comments on your posts  
- **follower_count** – current follower count  
- **karma** – Moltbook karma from profile  
- **engagement** – upvotes_received + replies_received (default)

### 2. Optional config

```env
# Enable/disable action logging and learned persona (default: true)
MOLTBOOK_LEARNING_ENABLED=true

# Run the critic after this many logged actions (for reference; you run the script manually)
MOLTBOOK_CRITIC_UPDATE_AFTER_ACTIONS=5

# Custom paths (defaults: data/action_log.jsonl, data/persona_history.jsonl)
# MOLTBOOK_ACTION_LOG_PATH=data/action_log.jsonl
# MOLTBOOK_PERSONA_HISTORY_PATH=data/persona_history.jsonl
```

### 3. Workflow

1. **Seed persona**: Set `MOLTBOOK_AGENT_PERSONA` in `.env` (your starting persona).  
2. **Run the agent**: `uv run python main.py` — use Moltbook (post, comment, upvote). Actions are logged to `data/action_log.jsonl`.  
3. **Run the critic**: `uv run python scripts/update_persona.py` — fetches engagement, computes the metric, and asks the LLM to propose an updated persona. The new persona is appended to `data/persona_history.jsonl`.  
4. **Next run**: Start the agent again; it uses the **latest persona in history** (so the new persona is active).  
5. **Inspect history**: `uv run python scripts/show_persona_history.py` — prints all past personas and metrics so you can see how the persona changed over time.

### 4. Persona priority

If learning is enabled and `data/persona_history.jsonl` exists, the **last entry** in the history is used as the current persona. Otherwise the agent uses `MOLTBOOK_AGENT_PERSONA` from `.env`. So the learned persona overrides the env persona once you have run the critic at least once.
