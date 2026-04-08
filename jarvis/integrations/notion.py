"""
Notion Integration
------------------
Monitors Notion databases for tasks, projects, and notes.
"""

from datetime import datetime

from integrations.base import BaseIntegration
from assistant.priority import PriorityItem
from config import NOTION_API_KEY, NOTION_DATABASE_IDS


class NotionIntegration(BaseIntegration):
    name = "notion"

    def __init__(self):
        self.client = None
        self.connected = False

    async def connect(self) -> bool:
        if not NOTION_API_KEY:
            print("[Notion] No API key configured")
            return False

        try:
            from notion_client import Client as NotionClient

            self.client = NotionClient(auth=NOTION_API_KEY)
            # Test connection
            self.client.users.me()
            self.connected = True
            return True

        except Exception as e:
            print(f"[Notion] Connection failed: {e}")
            self.connected = False
            return False

    async def fetch_items(self) -> list[PriorityItem]:
        if not self.connected or not self.client:
            return []

        items = []

        for db_id in NOTION_DATABASE_IDS:
            if not db_id.strip():
                continue

            try:
                results = self.client.databases.query(
                    database_id=db_id.strip(),
                    page_size=20,
                    sorts=[{"timestamp": "last_edited_time", "direction": "descending"}],
                )

                for page in results.get("results", []):
                    title = _extract_title(page)
                    status = _extract_status(page)
                    due_date = _extract_due_date(page)
                    url = page.get("url", "")

                    # Score based on status and due date
                    urgency = 3  # baseline
                    if status and status.lower() in ("in progress", "doing", "active"):
                        urgency += 2
                    if status and status.lower() in ("blocked", "stuck"):
                        urgency += 3
                    if due_date:
                        try:
                            due = datetime.fromisoformat(due_date)
                            days_until = (due - datetime.now()).days
                            if days_until < 0:
                                urgency += 4  # Overdue
                            elif days_until == 0:
                                urgency += 3  # Due today
                            elif days_until <= 2:
                                urgency += 2  # Due soon
                        except Exception:
                            pass

                    urgency = min(urgency, 10)

                    detail = f"Status: {status or 'N/A'}"
                    if due_date:
                        detail += f" | Due: {due_date}"

                    last_edited = page.get("last_edited_time", "")
                    try:
                        timestamp = datetime.fromisoformat(last_edited.replace("Z", "+00:00")).replace(tzinfo=None)
                    except Exception:
                        timestamp = datetime.now()

                    items.append(PriorityItem(
                        source="notion",
                        title=title,
                        detail=detail,
                        urgency=urgency,
                        timestamp=timestamp,
                        link=url,
                        tags=["notion", "task"],
                    ))

            except Exception as e:
                print(f"[Notion] Error fetching database {db_id}: {e}")

        return items

    async def get_context_summary(self) -> str:
        if not self.connected:
            return "Notion: Not connected. Configure NOTION_API_KEY to enable."

        items = await self.fetch_items()
        if not items:
            return "Notion: No active items found."

        lines = [f"Notion: {len(items)} items across your databases"]
        for item in sorted(items, key=lambda x: -x.urgency)[:10]:
            lines.append(f"  [{item.level}] {item.title}")
            lines.append(f"    {item.detail}")

        return "\n".join(lines)


def _extract_title(page: dict) -> str:
    """Extract the title from a Notion page."""
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            title_parts = prop.get("title", [])
            if title_parts:
                return "".join(t.get("plain_text", "") for t in title_parts)
    return "Untitled"


def _extract_status(page: dict) -> str | None:
    """Extract status from common property names."""
    props = page.get("properties", {})
    for name in ("Status", "status", "State", "state"):
        if name in props:
            prop = props[name]
            if prop.get("type") == "status":
                status = prop.get("status")
                return status.get("name") if status else None
            elif prop.get("type") == "select":
                select = prop.get("select")
                return select.get("name") if select else None
    return None


def _extract_due_date(page: dict) -> str | None:
    """Extract due date from common property names."""
    props = page.get("properties", {})
    for name in ("Due", "due", "Due Date", "due_date", "Deadline", "deadline", "Date", "date"):
        if name in props:
            prop = props[name]
            if prop.get("type") == "date":
                date_val = prop.get("date")
                if date_val:
                    return date_val.get("start")
    return None
