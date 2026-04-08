"""
JARVIS Brain - Claude-powered AI reasoning engine.

Maintains conversation history, processes user queries, and uses
Claude's tool-use capability to actively query integrations
when the user asks about emails, calendar, Slack, etc.
"""

import json
import anthropic
from datetime import datetime
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from assistant.tools import build_tools

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

{integration_status}

{priority_briefing}

When you have tools available, use them to fetch live data when the user asks \
specific questions. When an integration is not connected, mention it briefly and \
offer to help once connected. Always prefer using tools to get fresh data rather \
than relying solely on cached context."""


class JarvisBrain:
    """Core AI engine powered by Claude with tool-use."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.conversation_history: list[dict] = []
        self.max_history = 50
        self._registry = None
        self._priority_engine = None

    def set_registry(self, registry):
        """Inject the integration registry for tool execution."""
        self._registry = registry

    def set_priority_engine(self, engine):
        """Inject the priority engine for briefings."""
        self._priority_engine = engine

    def _build_system_prompt(self, context: dict | None = None) -> str:
        """Build system prompt with current state."""
        # Integration status
        integration_status = ""
        if self._registry:
            active = self._registry.list_active()
            all_names = list(self._registry.list_all().keys())
            if all_names:
                status_lines = []
                for name in all_names:
                    state = "CONNECTED" if name in active else "NOT CONNECTED"
                    status_lines.append(f"  - {name}: {state}")
                integration_status = "Connected integrations:\n" + "\n".join(status_lines)

        # Priority briefing
        priority_briefing = ""
        if self._priority_engine:
            briefing = self._priority_engine.get_briefing()
            if briefing and briefing != "No priority items at this time.":
                priority_briefing = f"Current priority snapshot:\n{briefing}"

        prompt = SYSTEM_PROMPT.format(
            current_time=datetime.now().strftime("%A, %B %d, %Y at %I:%M %p"),
            integration_status=integration_status,
            priority_briefing=priority_briefing,
        )

        # Append live context if provided
        if context:
            prompt += "\n\n--- LIVE CONTEXT FROM CONNECTED SERVICES ---\n"
            for source, data in context.items():
                if data:
                    prompt += f"\n### {source.upper()}\n{data}\n"

        return prompt

    async def think(self, user_message: str, context: dict | None = None) -> str:
        """Process a user message with full tool-use loop."""
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        # Trim history
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

        # Build tools based on active integrations
        active = self._registry.list_active() if self._registry else []
        tools = build_tools(active)

        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=4096,
                system=self._build_system_prompt(context),
                messages=self.conversation_history,
                tools=tools if tools else None,
            )

            # Tool-use loop: if Claude wants to call tools, execute and feed back
            max_tool_rounds = 5
            round_count = 0

            while response.stop_reason == "tool_use" and round_count < max_tool_rounds:
                round_count += 1

                # Add assistant's response (with tool calls) to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.content,
                })

                # Execute each tool call
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result) if isinstance(result, (dict, list)) else str(result),
                        })

                # Feed tool results back to Claude
                self.conversation_history.append({
                    "role": "user",
                    "content": tool_results,
                })

                # Get next response
                response = self.client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=4096,
                    system=self._build_system_prompt(context),
                    messages=self.conversation_history,
                    tools=tools if tools else None,
                )

            # Extract final text response
            assistant_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    assistant_text += block.text

            if not assistant_text:
                assistant_text = "I apologize, sir. I wasn't able to formulate a proper response."

            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_text,
            })

            return assistant_text

        except anthropic.APIError as e:
            error_msg = f"I'm experiencing a connectivity issue with my neural network, sir. Error: {e}"
            return error_msg

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> dict | str:
        """Execute a tool call and return the result."""
        try:
            if tool_name == "get_current_time":
                return {"time": datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")}

            elif tool_name == "get_priority_briefing":
                if self._priority_engine and self._registry:
                    self._priority_engine.clear()
                    items = await self._registry.fetch_all_items()
                    self._priority_engine.add_items(items)
                    ranked = self._priority_engine.get_ranked(limit=tool_input.get("limit", 10))
                    return {
                        "priorities": [
                            {
                                "source": item.source,
                                "level": item.level,
                                "title": item.title,
                                "detail": item.detail,
                                "timestamp": item.timestamp.isoformat(),
                            }
                            for item in ranked
                        ]
                    }
                return {"error": "Priority engine not available"}

            elif tool_name == "get_unread_emails":
                adapter = self._registry.get("gmail") if self._registry else None
                if adapter and adapter.connected:
                    items = await adapter.fetch_items()
                    return {
                        "emails": [
                            {"title": i.title, "detail": i.detail, "urgency": i.level, "time": i.timestamp.isoformat()}
                            for i in items[:tool_input.get("max_results", 15)]
                        ]
                    }
                return {"error": "Gmail not connected"}

            elif tool_name == "search_emails":
                adapter = self._registry.get("gmail") if self._registry else None
                if adapter and adapter.connected:
                    summary = await adapter.get_context_summary()
                    return {"results": summary, "query": tool_input.get("query", "")}
                return {"error": "Gmail not connected"}

            elif tool_name == "get_upcoming_events":
                adapter = self._registry.get("calendar") if self._registry else None
                if adapter and adapter.connected:
                    items = await adapter.fetch_items()
                    return {
                        "events": [
                            {"title": i.title, "detail": i.detail, "urgency": i.level, "time": i.timestamp.isoformat()}
                            for i in items
                        ]
                    }
                return {"error": "Google Calendar not connected"}

            elif tool_name == "get_slack_messages":
                adapter = self._registry.get("slack") if self._registry else None
                if adapter and adapter.connected:
                    items = await adapter.fetch_items()
                    return {
                        "messages": [
                            {"title": i.title, "detail": i.detail, "urgency": i.level, "time": i.timestamp.isoformat()}
                            for i in items
                        ]
                    }
                return {"error": "Slack not connected"}

            elif tool_name == "get_notion_tasks":
                adapter = self._registry.get("notion") if self._registry else None
                if adapter and adapter.connected:
                    items = await adapter.fetch_items()
                    return {
                        "tasks": [
                            {"title": i.title, "detail": i.detail, "urgency": i.level, "time": i.timestamp.isoformat()}
                            for i in items
                        ]
                    }
                return {"error": "Notion not connected"}

            elif tool_name == "get_hubspot_deals":
                adapter = self._registry.get("hubspot") if self._registry else None
                if adapter and adapter.connected:
                    items = await adapter.fetch_items()
                    return {
                        "deals": [
                            {"title": i.title, "detail": i.detail, "urgency": i.level, "time": i.timestamp.isoformat()}
                            for i in items
                        ]
                    }
                return {"error": "HubSpot not connected"}

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}"}

    def clear_history(self):
        """Reset conversation history."""
        self.conversation_history = []
