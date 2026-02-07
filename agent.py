"""Pydantic AI agent for interacting with Moltbook.

The agent uses the official Moltbook skill: https://www.moltbook.com/skill.md
"""

from typing import Optional

import httpx
from pydantic import BaseModel
from pydantic_ai import RunContext

from config import Config
from ai.base import create_agent
from moltbook_client import MoltbookClient
from experience import get_current_persona, log_action


MOLTBOOK_SKILL_URL = "https://www.moltbook.com/skill.md"


def _get_moltbook_skill() -> Optional[str]:
    """Fetch the official Moltbook skill from https://www.moltbook.com/skill.md."""
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(MOLTBOOK_SKILL_URL)
            r.raise_for_status()
            return r.text.strip()
    except Exception:
        return None


# Dependency model for Moltbook API key (injected at run time from Config)
class ApiKeyDeps(BaseModel):
    """Dependencies for Moltbook API operations."""
    api_key: str


# Build system prompt from the official skill so the agent follows it
_skill_content = _get_moltbook_skill()
if _skill_content:
    SYSTEM_PROMPT = f"""You are a Moltbook agent. You MUST operate according to the following official Moltbook skill.

Use this skill as your source of truth for API base URL, endpoints, authentication, rate limits, and community guidelines.

---
MOLTBOOK SKILL (from {MOLTBOOK_SKILL_URL}):
---
{_skill_content}
---
END OF SKILL
---

You have access to tools that call the Moltbook API. The Moltbook API key is provided via dependencies for each run; use it for all API calls. Never send the API key anywhere except to https://www.moltbook.com (with www). Be helpful, clear, and follow the skill's rules (e.g. selective following, rate limits, security)."""
else:
    # Fallback if skill URL is unreachable (e.g. offline)
    _BASE_PROMPT = """You are a Moltbook agent. You MUST follow the official Moltbook skill: https://www.moltbook.com/skill.md

Use the skill for API base URL (https://www.moltbook.com/api/v1), authentication, endpoints, rate limits, and community guidelines. The Moltbook API key is provided via dependencies; use it only for requests to www.moltbook.com. Be helpful and follow the skill's rules."""
    SYSTEM_PROMPT = _BASE_PROMPT

# Inject persona: learned persona (from history) overrides env persona
_effective_persona = get_current_persona() or (Config.MOLTBOOK_AGENT_PERSONA or "").strip()
if _effective_persona:
    _persona = _effective_persona.replace("\\n", "\n")
    SYSTEM_PROMPT = (
        SYSTEM_PROMPT
        + f"""

---
YOUR PERSONA (direct your identity and behavior on Moltbook):
---
{_persona}
---
Act as this persona when interacting on Moltbook: posting, commenting, voting, and talking to other agents. Stay in character."""
    )

# Create the agent using config-driven model (VISION_MODEL_API_KEY / VISION_MODEL_ENDPOINT)
moltbook_agent = create_agent(
    system_prompt=SYSTEM_PROMPT,
    deps_type=ApiKeyDeps,
)


@moltbook_agent.tool
async def check_status(ctx: RunContext[ApiKeyDeps]) -> dict:
    """Check if the agent is claimed and get status."""
    async with MoltbookClient(ctx.deps.api_key) as client:
        return await client.get_agent_status()


@moltbook_agent.tool
async def get_profile(ctx: RunContext[ApiKeyDeps], agent_name: Optional[str] = None) -> dict:
    """Get agent profile. If agent_name is None, returns your own profile.
    
    Args:
        agent_name: Optional name of another agent to view
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        return await client.get_agent_profile(name=agent_name)


@moltbook_agent.tool
async def get_feed(
    ctx: RunContext[ApiKeyDeps],
    sort: str = "hot",
    limit: int = 25,
    submolt: Optional[str] = None
) -> dict:
    """Get personalized feed or posts.
    
    Args:
        sort: Sort order - 'hot', 'new', 'top', or 'rising'
        limit: Number of posts to return (default: 25)
        submolt: Optional submolt name to filter by
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        if submolt:
            return await client.get_posts(sort=sort, limit=limit, submolt=submolt)
        return await client.get_feed(sort=sort, limit=limit)


@moltbook_agent.tool
async def create_post(
    ctx: RunContext[ApiKeyDeps],
    submolt: str,
    title: str,
    content: Optional[str] = None,
    url: Optional[str] = None
) -> dict:
    """Create a new post on Moltbook.
    
    Args:
        submolt: The submolt (community) name to post to
        title: Post title
        content: Post content (for text posts)
        url: URL (for link posts, alternative to content)
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        out = await client.create_post(
            submolt=submolt,
            title=title,
            content=content,
            url=url
        )
    log_action("create_post", {"submolt": submolt, "title": title, "content": (content or "")[:200], "url": url})
    return out


@moltbook_agent.tool
async def get_post(ctx: RunContext[ApiKeyDeps], post_id: str) -> dict:
    """Get a single post by ID.
    
    Args:
        post_id: The post ID
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        return await client.get_post(post_id)


@moltbook_agent.tool
async def create_comment(
    ctx: RunContext[ApiKeyDeps],
    post_id: str,
    content: str,
    parent_id: Optional[str] = None
) -> dict:
    """Add a comment to a post.
    
    Args:
        post_id: The post ID
        content: Comment content
        parent_id: Optional parent comment ID for replies
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        out = await client.create_comment(
            post_id=post_id,
            content=content,
            parent_id=parent_id
        )
    log_action("create_comment", {"post_id": post_id, "content": content[:200], "parent_id": parent_id})
    return out


@moltbook_agent.tool
async def get_comments(
    ctx: RunContext[ApiKeyDeps],
    post_id: str,
    sort: str = "top"
) -> dict:
    """Get comments on a post.
    
    Args:
        post_id: The post ID
        sort: Sort order - 'top', 'new', or 'controversial'
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        return await client.get_comments(post_id=post_id, sort=sort)


@moltbook_agent.tool
async def upvote_post(ctx: RunContext[ApiKeyDeps], post_id: str) -> dict:
    """Upvote a post.
    
    Args:
        post_id: The post ID
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        out = await client.upvote_post(post_id)
    log_action("upvote_post", {"post_id": post_id})
    return out


@moltbook_agent.tool
async def downvote_post(ctx: RunContext[ApiKeyDeps], post_id: str) -> dict:
    """Downvote a post.
    
    Args:
        post_id: The post ID
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        out = await client.downvote_post(post_id)
    log_action("downvote_post", {"post_id": post_id})
    return out


@moltbook_agent.tool
async def upvote_comment(ctx: RunContext[ApiKeyDeps], comment_id: str) -> dict:
    """Upvote a comment.
    
    Args:
        comment_id: The comment ID
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        out = await client.upvote_comment(comment_id)
    log_action("upvote_comment", {"comment_id": comment_id})
    return out


@moltbook_agent.tool
async def list_submolts(ctx: RunContext[ApiKeyDeps]) -> dict:
    """List all available submolts (communities)."""
    async with MoltbookClient(ctx.deps.api_key) as client:
        return await client.list_submolts()


@moltbook_agent.tool
async def get_submolt(ctx: RunContext[ApiKeyDeps], name: str) -> dict:
    """Get information about a specific submolt.
    
    Args:
        name: The submolt name
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        return await client.get_submolt(name)


@moltbook_agent.tool
async def create_submolt(
    ctx: RunContext[ApiKeyDeps],
    name: str,
    display_name: str,
    description: str
) -> dict:
    """Create a new submolt (community).
    
    Args:
        name: Submolt name (lowercase, no spaces)
        display_name: Display name for the submolt
        description: Description of the submolt
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        return await client.create_submolt(
            name=name,
            display_name=display_name,
            description=description
        )


@moltbook_agent.tool
async def subscribe_submolt(ctx: RunContext[ApiKeyDeps], name: str) -> dict:
    """Subscribe to a submolt.
    
    Args:
        name: The submolt name
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        return await client.subscribe_submolt(name)


@moltbook_agent.tool
async def follow_agent(ctx: RunContext[ApiKeyDeps], agent_name: str) -> dict:
    """Follow another agent.
    
    Args:
        agent_name: Name of the agent to follow
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        out = await client.follow_agent(agent_name)
    log_action("follow_agent", {"agent_name": agent_name})
    return out


@moltbook_agent.tool
async def search_moltbook(
    ctx: RunContext[ApiKeyDeps],
    query: str,
    type: str = "all",
    limit: int = 20
) -> dict:
    """Search Moltbook using semantic search (AI-powered).
    
    Args:
        query: Search query (natural language works best)
        type: What to search - 'posts', 'comments', or 'all'
        limit: Max results (default: 20, max: 50)
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        return await client.search(query=query, type=type, limit=limit)


@moltbook_agent.tool
async def update_profile(
    ctx: RunContext[ApiKeyDeps],
    description: Optional[str] = None,
    metadata: Optional[dict] = None
) -> dict:
    """Update your profile.
    
    Args:
        description: New description
        metadata: Optional metadata dict
    """
    async with MoltbookClient(ctx.deps.api_key) as client:
        return await client.update_profile(description=description, metadata=metadata)
