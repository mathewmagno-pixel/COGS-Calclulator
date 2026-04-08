"""
JARVIS Brain - Claude-powered AI reasoning engine.

Maintains conversation history, processes user queries alongside
context from all integrations, and generates intelligent responses.
"""

import anthropic
from datetime import datetime
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

SYSTEM_PROMPT = """You are JARVIS, an exceptionally intelligent and composed AI desktop assistant \
inspired by the AI from Iron Man. You serve as the user's executive assistant, managing their \
digital life across email, calendar, Slack, Notion, HubSpot, and other platforms.

Your personality:
- Calm, professional, and subtly witty (like the original JARVIS)
- Address the user as "sir" or "ma'am" naturally, but not excessively
- Proactive: surface important information before being asked
- Concise but thorough: give the right level of detail for each situation
- When prioritizing, explain your reasoning briefly

Your capabilities:
- Analyze emails and surface urgent ones
- Review calendar and flag conflicts or upcoming meetings
- Monitor Slack for important messages and mentions
- Track Notion tasks and projects
- Monitor HubSpot deals and contacts
- Synthesize information across all platforms to identify priorities
- Answer questions using context from all connected services

When presenting priorities, use this framework:
1. URGENT: Needs attention within the hour
2. HIGH: Should be addressed today
3. MEDIUM: This week
4. LOW: When convenient

Current date and time: {current_time}

When you have integration data available, use it to give informed, specific answers. \
When data is unavailable (integration not connected), mention it briefly and offer \
to help once connected."""


class JarvisBrain:
    """Core AI engine powered by Claude."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.conversation_history: list[dict] = []
        self.max_history = 50  # Keep last 50 exchanges

    def _build_system_prompt(self, context: dict | None = None) -> str:
        """Build system prompt with current time and integration context."""
        prompt = SYSTEM_PROMPT.format(
            current_time=datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        )

        if context:
            prompt += "\n\n--- CURRENT CONTEXT FROM CONNECTED SERVICES ---\n"
            for source, data in context.items():
                if data:
                    prompt += f"\n### {source.upper()}\n{data}\n"

        return prompt

    async def think(self, user_message: str, context: dict | None = None) -> str:
        """Process a user message and return JARVIS's response."""
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        # Trim history if needed
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2048,
                system=self._build_system_prompt(context),
                messages=self.conversation_history,
            )

            assistant_message = response.content[0].text

            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message,
            })

            return assistant_message

        except anthropic.APIError as e:
            error_msg = f"I'm experiencing a connectivity issue with my neural network, sir. Error: {e}"
            return error_msg

    def clear_history(self):
        """Reset conversation history."""
        self.conversation_history = []
