"""
HubSpot Integration
-------------------
Monitors HubSpot for deals, contacts, and tasks that need attention.
"""

from datetime import datetime

from integrations.base import BaseIntegration
from assistant.priority import PriorityItem
from config import HUBSPOT_API_KEY


class HubSpotIntegration(BaseIntegration):
    name = "hubspot"

    def __init__(self):
        self.client = None
        self.connected = False

    async def connect(self) -> bool:
        if not HUBSPOT_API_KEY:
            print("[HubSpot] No API key configured")
            return False

        try:
            from hubspot import HubSpot

            self.client = HubSpot(access_token=HUBSPOT_API_KEY)
            # Test connection
            self.client.crm.contacts.basic_api.get_page(limit=1)
            self.connected = True
            return True

        except Exception as e:
            print(f"[HubSpot] Connection failed: {e}")
            self.connected = False
            return False

    async def fetch_items(self) -> list[PriorityItem]:
        if not self.connected or not self.client:
            return []

        items = []

        # Fetch recent deals
        try:
            deals = self.client.crm.deals.basic_api.get_page(
                limit=20,
                properties=["dealname", "dealstage", "amount", "closedate", "hubspot_owner_id"],
                sorts=["-hs_lastmodifieddate"],
            )

            for deal in deals.results:
                props = deal.properties
                name = props.get("dealname", "Untitled Deal")
                stage = props.get("dealstage", "unknown")
                amount = props.get("amount", "")
                close_date_str = props.get("closedate", "")

                urgency = 3
                detail_parts = [f"Stage: {stage}"]

                if amount:
                    detail_parts.append(f"Amount: ${float(amount):,.2f}")

                if close_date_str:
                    try:
                        close_date = datetime.fromisoformat(close_date_str.replace("Z", "+00:00")).replace(tzinfo=None)
                        days_until = (close_date - datetime.now()).days
                        detail_parts.append(f"Closes: {close_date.strftime('%b %d')}")

                        if days_until < 0:
                            urgency += 3  # Overdue
                        elif days_until <= 3:
                            urgency += 2  # Closing soon
                        elif days_until <= 7:
                            urgency += 1
                    except Exception:
                        pass

                # High-value deals get priority bump
                if amount and float(amount) > 10000:
                    urgency += 1
                if amount and float(amount) > 50000:
                    urgency += 1

                urgency = min(urgency, 10)

                items.append(PriorityItem(
                    source="hubspot",
                    title=f"Deal: {name}",
                    detail=" | ".join(detail_parts),
                    urgency=urgency,
                    timestamp=datetime.fromisoformat(
                        deal.properties.get("hs_lastmodifieddate", datetime.now().isoformat())
                        .replace("Z", "+00:00")
                    ).replace(tzinfo=None) if deal.properties.get("hs_lastmodifieddate") else datetime.now(),
                    link=f"https://app.hubspot.com/contacts/deals/{deal.id}",
                    tags=["hubspot", "deal"],
                ))

        except Exception as e:
            print(f"[HubSpot] Error fetching deals: {e}")

        # Fetch tasks/engagements
        try:
            tasks = self.client.crm.objects.basic_api.get_page(
                object_type="tasks",
                limit=15,
                properties=["hs_task_subject", "hs_task_status", "hs_task_priority",
                             "hs_timestamp"],
            )

            for task in tasks.results:
                props = task.properties
                subject = props.get("hs_task_subject", "Untitled Task")
                status = props.get("hs_task_status", "")
                priority = props.get("hs_task_priority", "")

                if status == "COMPLETED":
                    continue

                urgency = 4
                if priority == "HIGH":
                    urgency += 3
                elif priority == "MEDIUM":
                    urgency += 1

                urgency = min(urgency, 10)

                items.append(PriorityItem(
                    source="hubspot",
                    title=f"Task: {subject}",
                    detail=f"Status: {status} | Priority: {priority}",
                    urgency=urgency,
                    timestamp=datetime.now(),
                    link=f"https://app.hubspot.com/contacts/tasks/{task.id}",
                    tags=["hubspot", "task"],
                ))

        except Exception as e:
            print(f"[HubSpot] Error fetching tasks: {e}")

        return items

    async def get_context_summary(self) -> str:
        if not self.connected:
            return "HubSpot: Not connected. Configure HUBSPOT_API_KEY to enable."

        items = await self.fetch_items()
        if not items:
            return "HubSpot: No active deals or tasks."

        deals = [i for i in items if "deal" in i.tags]
        tasks = [i for i in items if "task" in i.tags]

        lines = [f"HubSpot: {len(deals)} active deals, {len(tasks)} open tasks"]

        if deals:
            lines.append("  Deals:")
            for item in sorted(deals, key=lambda x: -x.urgency)[:5]:
                lines.append(f"    [{item.level}] {item.title}")
                lines.append(f"      {item.detail}")

        if tasks:
            lines.append("  Tasks:")
            for item in sorted(tasks, key=lambda x: -x.urgency)[:5]:
                lines.append(f"    [{item.level}] {item.title}")

        return "\n".join(lines)
