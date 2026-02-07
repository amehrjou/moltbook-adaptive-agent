"""Base AI agent configuration and utilities."""

import os
from typing import Optional

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel

from config import Config


def build_azure_openai_model(
    *,
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    deployment: Optional[str] = None,
    api_version: Optional[str] = None,
    model_name: Optional[str] = None,
) -> OpenAIChatModel:
    """
    Build an OpenAIChatModel backed by an Azure OpenAI deployment.

    Args:
        api_key: Azure OpenAI API key. Defaults to Config.
        endpoint: Azure OpenAI endpoint URL. Defaults to Config.
        deployment: Azure deployment name. Defaults to Config.
        api_version: Azure API version. Defaults to Config.
        model_name: Optional model name. Defaults to deployment.

    Returns:
        Configured OpenAIChatModel for Pydantic AI Agent.
    """
    api_key = api_key or Config.VISION_MODEL_API_KEY
    endpoint = endpoint or Config.VISION_MODEL_ENDPOINT
    deployment = deployment or Config.VISION_MODEL_DEPLOYMENT
    api_version = api_version or Config.VISION_MODEL_API_VERSION

    if not api_key:
        raise ValueError("Azure OpenAI API key is required.")
    if not endpoint:
        raise ValueError("Azure OpenAI endpoint is required.")
    if not deployment:
        raise ValueError("Azure OpenAI deployment name is required.")

    from openai import AsyncAzureOpenAI
    from pydantic_ai.providers.openai import OpenAIProvider

    client = AsyncAzureOpenAI(
        api_key=api_key,
        api_version=api_version or "2024-02-15-preview",
        azure_endpoint=endpoint.rstrip("/"),
    )
    provider = OpenAIProvider(openai_client=client)
    return OpenAIChatModel(
        model_name=model_name or deployment,
        provider=provider,
    )


def get_default_model() -> OpenAIChatModel:
    """
    Get default AI model based on configuration.

    Supports both standard OpenAI and Azure OpenAI endpoints.
    Uses VISION_MODEL_API_KEY and VISION_MODEL_ENDPOINT from config.

    Returns:
        Configured AI model instance
    """
    api_key = Config.VISION_MODEL_API_KEY
    if not api_key:
        raise ValueError(
            "VISION_MODEL_API_KEY not set in environment variables. "
            "Please set it in your .env file."
        )

    if Config.AZURE_OPENAI_ENABLED:
        return build_azure_openai_model(
            api_key=api_key,
            endpoint=Config.VISION_MODEL_ENDPOINT,
            deployment=Config.VISION_MODEL_DEPLOYMENT,
            api_version=Config.VISION_MODEL_API_VERSION,
        )

    # Standard OpenAI: set API key in environment (provider reads it)
    if not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = api_key

    model_name = "gpt-4o-mini"
    endpoint = Config.VISION_MODEL_ENDPOINT

    if endpoint:
        from pydantic_ai.providers.openai import OpenAIProvider
        provider = OpenAIProvider(api_key=api_key, base_url=endpoint.rstrip("/"))
        return OpenAIChatModel(model_name=model_name, provider=provider)

    return OpenAIChatModel(model_name=model_name, provider="openai")


def create_agent(
    model: Optional[OpenAIChatModel] = None,
    system_prompt: str = "",
    output_type=None,
    **kwargs,
) -> Agent:
    """
    Create a Pydantic AI agent with default configuration.

    Args:
        model: AI model to use. If None, uses default from config.
        system_prompt: System prompt for the agent.
        output_type: Pydantic model class for structured output.
        **kwargs: Additional agent configuration (e.g. deps_type).

    Returns:
        Configured Pydantic AI agent
    """
    if model is None:
        model = get_default_model()

    agent_kwargs = {
        "model": model,
        "system_prompt": system_prompt,
        **kwargs,
    }
    if output_type is not None:
        agent_kwargs["output_type"] = output_type
    return Agent(**agent_kwargs)
