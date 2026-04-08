"""
JARVIS Tool Definitions for Claude Tool-Use
---------------------------------------------
These tools allow Claude to actively query and act on integrations
rather than just reading static context. When the user asks a question,
Claude can call these tools to fetch live data.
"""


def build_tools(active_integrations: list[str]) -> list[dict]:
    """Build tool definitions based on which integrations are active."""
    tools = [
        # Always available
        {
            "name": "get_priority_briefing",
            "description": "Get a ranked list of the user's current priorities across all connected services. Call this when the user asks about their priorities, what they should focus on, or wants a status update.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max number of items to return (default 10)",
                        "default": 10,
                    }
                },
                "required": [],
            },
        },
        {
            "name": "get_current_time",
            "description": "Get the current date and time.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]

    if "gmail" in active_integrations:
        tools.extend([
            {
                "name": "search_emails",
                "description": "Search the user's Gmail inbox. Use this when they ask about specific emails, senders, or topics.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Gmail search query (e.g., 'from:boss@company.com', 'subject:invoice', 'is:unread')",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Max emails to return (default 10)",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_unread_emails",
                "description": "Get the user's unread emails from their inbox. Call when they ask about new/unread emails.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "max_results": {
                            "type": "integer",
                            "description": "Max emails to return (default 15)",
                            "default": 15,
                        },
                    },
                    "required": [],
                },
            },
        ])

    if "calendar" in active_integrations:
        tools.extend([
            {
                "name": "get_upcoming_events",
                "description": "Get upcoming calendar events. Call when the user asks about their schedule, meetings, or what's coming up.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "hours_ahead": {
                            "type": "integer",
                            "description": "How many hours ahead to look (default 24)",
                            "default": 24,
                        },
                    },
                    "required": [],
                },
            },
        ])

    if "slack" in active_integrations:
        tools.extend([
            {
                "name": "get_slack_messages",
                "description": "Get recent Slack messages including DMs and mentions. Call when the user asks about Slack messages or who messaged them.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "hours_back": {
                            "type": "integer",
                            "description": "How many hours back to look (default 4)",
                            "default": 4,
                        },
                    },
                    "required": [],
                },
            },
        ])

    if "notion" in active_integrations:
        tools.extend([
            {
                "name": "get_notion_tasks",
                "description": "Get tasks and items from the user's Notion databases. Call when they ask about tasks, projects, or Notion items.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ])

    if "hubspot" in active_integrations:
        tools.extend([
            {
                "name": "get_hubspot_deals",
                "description": "Get active deals and tasks from HubSpot CRM. Call when the user asks about deals, pipeline, or CRM data.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ])

    return tools
