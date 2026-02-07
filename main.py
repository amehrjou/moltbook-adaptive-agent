"""Main entry point for the Moltbook agentic system."""

import asyncio

from config import Config
from agent import moltbook_agent, ApiKeyDeps


async def main():
    """Main function to interact with the Moltbook agent."""
    # API key from Config (env MOLTBOOK_API_KEY or api_alone file – same pattern as portfolio_os)
    api_key = Config.MOLTBOOK_API_KEY
    if not api_key:
        print("Error: MOLTBOOK_API_KEY not found in environment or api_alone file")
        print("Please set MOLTBOOK_API_KEY in .env or create api_alone file")
        return

    print("🦞 Moltbook Agentic System")
    print("=" * 50)
    print(f"Using API key: {api_key[:20]}...")
    if Config.MOLTBOOK_AGENT_PERSONA and Config.MOLTBOOK_AGENT_PERSONA.strip():
        print("Persona: " + Config.MOLTBOOK_AGENT_PERSONA.strip()[:80].replace("\n", " ") + ("..." if len(Config.MOLTBOOK_AGENT_PERSONA.strip()) > 80 else ""))
    print()
    deps = ApiKeyDeps(api_key=api_key)

    # Check status
    print("Checking agent status...")
    result = await moltbook_agent.run("Check my status on Moltbook.", deps=deps)
    print(f"Status: {result.output}")
    print()

    # Get feed
    print("Getting latest feed...")
    result = await moltbook_agent.run(
        "Get the latest hot posts from my feed.", deps=deps
    )
    print(f"Feed: {result.output}")
    print()

    # Interactive mode
    print("Entering interactive mode. Type 'exit' to quit.")
    print()
    print("You can:")
    print("  • Give direct commands: 'Post in general: Hello Moltbook!', 'Search for agent memory'")
    print("  • Let the agent work freely: 'Go check Moltbook and engage with the community' or 'Browse the feed and reply to one interesting post'")
    print("  • Ask about you: 'What’s my profile?', 'List my subscribed submolts'")
    print()
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye! 🦞")
                break
            
            if not user_input:
                continue

            result = await moltbook_agent.run(user_input, deps=deps)
            print(f"\nAgent: {result.output}\n")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! 🦞")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
