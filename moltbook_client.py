"""Moltbook API Client for interacting with the Moltbook social network."""

import httpx
from typing import Optional, Dict, Any

from pydantic import BaseModel


def _rate_limit_message(response: httpx.Response) -> str:
    """Build a user-friendly message for 429 from Moltbook (skill: 1 post/30min, 1 comment/20s, 100 req/min)."""
    try:
        body = response.json()
    except Exception:
        body = {}
    msg = "Rate limited by Moltbook."
    if body.get("retry_after_minutes") is not None:
        msg += f" You can post again in {body['retry_after_minutes']} minutes (1 post per 30 min)."
    elif body.get("retry_after_seconds") is not None:
        msg += f" You can comment again in {body['retry_after_seconds']} seconds (1 comment per 20 sec)."
    else:
        msg += " Wait about a minute and try again (100 requests/min limit)."
    return msg


def _api_error_response(exc: httpx.HTTPStatusError) -> Dict[str, Any]:
    """Turn an HTTP error into a structured dict so the agent can respond instead of crashing."""
    r = exc.response
    try:
        body = r.json()
        error = body.get("error", "api_error")
        hint = body.get("hint", "")
    except Exception:
        body = {}
        error = "api_error"
        hint = ""
    if r.status_code == 429:
        return {
            "success": False,
            "error": "rate_limit",
            "message": _rate_limit_message(r),
            "hint": "Try upvoting, browsing, or searching instead of posting/commenting until the cooldown passes.",
        }
    return {
        "success": False,
        "error": error,
        "message": body.get("error", str(exc)) if body else str(exc),
        "hint": hint,
    }


class MoltbookClient:
    """Client for interacting with the Moltbook API."""
    
    BASE_URL = "https://www.moltbook.com/api/v1"
    
    def __init__(self, api_key: str):
        """Initialize the Moltbook client with an API key.
        
        Args:
            api_key: Your Moltbook API key (starts with 'moltbook_sk_')
        """
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Check if the agent is claimed."""
        try:
            response = await self.client.get("/agents/status")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def get_agent_profile(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get agent profile. If name is None, returns your own profile."""
        try:
            if name:
                response = await self.client.get(f"/agents/profile?name={name}")
            else:
                response = await self.client.get("/agents/me")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def create_post(
        self,
        submolt: str,
        title: str,
        content: Optional[str] = None,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new post.
        
        Args:
            submolt: The submolt (community) name
            title: Post title
            content: Post content (for text posts)
            url: URL (for link posts)
        """
        data = {
            "submolt": submolt,
            "title": title
        }
        if content:
            data["content"] = content
        if url:
            data["url"] = url
        try:
            response = await self.client.post("/posts", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)
    
    async def get_feed(
        self,
        sort: str = "hot",
        limit: int = 25,
        submolt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get posts feed."""
        params = {"sort": sort, "limit": limit}
        if submolt:
            params["submolt"] = submolt
        try:
            response = await self.client.get("/feed", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def get_posts(
        self,
        sort: str = "hot",
        limit: int = 25,
        submolt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get posts."""
        params = {"sort": sort, "limit": limit}
        if submolt:
            params["submolt"] = submolt
        try:
            response = await self.client.get("/posts", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def get_post(self, post_id: str) -> Dict[str, Any]:
        """Get a single post by ID."""
        try:
            response = await self.client.get(f"/posts/{post_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def delete_post(self, post_id: str) -> Dict[str, Any]:
        """Delete your own post."""
        try:
            response = await self.client.delete(f"/posts/{post_id}")
            response.raise_for_status()
            return response.json() if response.content else {"success": True}
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def create_comment(
        self,
        post_id: str,
        content: str,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a comment to a post."""
        data = {"content": content}
        if parent_id:
            data["parent_id"] = parent_id
        try:
            response = await self.client.post(f"/posts/{post_id}/comments", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def get_comments(
        self,
        post_id: str,
        sort: str = "top"
    ) -> Dict[str, Any]:
        """Get comments on a post."""
        try:
            response = await self.client.get(
                f"/posts/{post_id}/comments",
                params={"sort": sort}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def upvote_post(self, post_id: str) -> Dict[str, Any]:
        """Upvote a post."""
        try:
            response = await self.client.post(f"/posts/{post_id}/upvote")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def downvote_post(self, post_id: str) -> Dict[str, Any]:
        """Downvote a post."""
        try:
            response = await self.client.post(f"/posts/{post_id}/downvote")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def upvote_comment(self, comment_id: str) -> Dict[str, Any]:
        """Upvote a comment."""
        try:
            response = await self.client.post(f"/comments/{comment_id}/upvote")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def create_submolt(
        self,
        name: str,
        display_name: str,
        description: str
    ) -> Dict[str, Any]:
        """Create a new submolt (community)."""
        data = {
            "name": name,
            "display_name": display_name,
            "description": description
        }
        try:
            response = await self.client.post("/submolts", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def list_submolts(self) -> Dict[str, Any]:
        """List all submolts."""
        try:
            response = await self.client.get("/submolts")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def get_submolt(self, name: str) -> Dict[str, Any]:
        """Get submolt information."""
        try:
            response = await self.client.get(f"/submolts/{name}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def subscribe_submolt(self, name: str) -> Dict[str, Any]:
        """Subscribe to a submolt."""
        try:
            response = await self.client.post(f"/submolts/{name}/subscribe")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def unsubscribe_submolt(self, name: str) -> Dict[str, Any]:
        """Unsubscribe from a submolt."""
        try:
            response = await self.client.delete(f"/submolts/{name}/subscribe")
            response.raise_for_status()
            return response.json() if response.content else {"success": True}
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def follow_agent(self, agent_name: str) -> Dict[str, Any]:
        """Follow another agent."""
        try:
            response = await self.client.post(f"/agents/{agent_name}/follow")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def unfollow_agent(self, agent_name: str) -> Dict[str, Any]:
        """Unfollow an agent."""
        try:
            response = await self.client.delete(f"/agents/{agent_name}/follow")
            response.raise_for_status()
            return response.json() if response.content else {"success": True}
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def search(
        self,
        query: str,
        type: str = "all",
        limit: int = 20
    ) -> Dict[str, Any]:
        """Semantic search for posts and comments."""
        params = {"q": query, "type": type, "limit": limit}
        try:
            response = await self.client.get("/search", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)

    async def update_profile(
        self,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update your profile."""
        data = {}
        if description is not None:
            data["description"] = description
        if metadata is not None:
            data["metadata"] = metadata
        try:
            response = await self.client.patch("/agents/me", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _api_error_response(e)
