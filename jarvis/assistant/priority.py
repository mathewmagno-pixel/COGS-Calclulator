"""
JARVIS Priority Engine
----------------------
Aggregates data from all connected integrations and produces
a ranked priority briefing. Uses time-sensitivity, sender importance,
and content signals to score items.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field


@dataclass
class PriorityItem:
    """A single actionable item from any integration."""
    source: str          # e.g. "gmail", "slack", "calendar"
    title: str           # Brief description
    detail: str          # Full context
    urgency: int         # 1-10 scale (10 = most urgent)
    timestamp: datetime
    link: str = ""       # Direct link to the item
    tags: list[str] = field(default_factory=list)

    @property
    def level(self) -> str:
        if self.urgency >= 8:
            return "URGENT"
        elif self.urgency >= 6:
            return "HIGH"
        elif self.urgency >= 4:
            return "MEDIUM"
        return "LOW"


class PriorityEngine:
    """Aggregates and ranks items from all integrations."""

    def __init__(self):
        self.items: list[PriorityItem] = []

    def clear(self):
        self.items = []

    def add_items(self, items: list[PriorityItem]):
        self.items.extend(items)

    def get_ranked(self, limit: int = 20) -> list[PriorityItem]:
        """Return items sorted by urgency (highest first)."""
        return sorted(self.items, key=lambda x: (-x.urgency, x.timestamp))[:limit]

    def get_briefing(self) -> str:
        """Generate a text briefing of current priorities for the AI brain."""
        ranked = self.get_ranked()
        if not ranked:
            return "No priority items at this time."

        lines = ["Here are your current priorities:\n"]
        current_level = None

        for item in ranked:
            if item.level != current_level:
                current_level = item.level
                lines.append(f"\n--- {current_level} ---")

            age = _format_age(item.timestamp)
            lines.append(f"  [{item.source.upper()}] {item.title} ({age})")
            if item.detail:
                # Truncate long details
                detail = item.detail[:200] + "..." if len(item.detail) > 200 else item.detail
                lines.append(f"    {detail}")

        return "\n".join(lines)

    def score_email(self, subject: str, sender: str, snippet: str, date: datetime) -> int:
        """Heuristic scoring for emails."""
        score = 3  # baseline

        # Time sensitivity
        hours_old = (datetime.now() - date).total_seconds() / 3600
        if hours_old < 1:
            score += 3
        elif hours_old < 4:
            score += 2
        elif hours_old < 12:
            score += 1

        # Content signals
        urgent_words = ["urgent", "asap", "critical", "deadline", "immediately", "action required"]
        text = f"{subject} {snippet}".lower()
        if any(w in text for w in urgent_words):
            score += 3

        # Meeting/calendar related
        if any(w in text for w in ["meeting", "invite", "calendar", "schedule"]):
            score += 1

        return min(score, 10)

    def score_calendar_event(self, summary: str, start: datetime) -> int:
        """Heuristic scoring for calendar events."""
        now = datetime.now()
        delta = start - now

        if delta < timedelta(minutes=15):
            return 10  # Imminent
        elif delta < timedelta(hours=1):
            return 8
        elif delta < timedelta(hours=3):
            return 6
        elif delta < timedelta(hours=8):
            return 4
        return 2

    def score_slack_message(self, text: str, is_mention: bool, is_dm: bool, date: datetime) -> int:
        """Heuristic scoring for Slack messages."""
        score = 2

        if is_dm:
            score += 3
        if is_mention:
            score += 2

        hours_old = (datetime.now() - date).total_seconds() / 3600
        if hours_old < 1:
            score += 2
        elif hours_old < 4:
            score += 1

        urgent_words = ["urgent", "asap", "help", "blocked", "down", "broken"]
        if any(w in text.lower() for w in urgent_words):
            score += 2

        return min(score, 10)


def _format_age(dt: datetime) -> str:
    """Format a datetime as a human-readable age string."""
    delta = datetime.now() - dt
    seconds = delta.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = int(seconds / 60)
        return f"{mins}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    else:
        days = int(seconds / 86400)
        return f"{days}d ago"
