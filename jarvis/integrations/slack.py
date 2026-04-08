"""
Slack Integration
-----------------
Monitors Slack for unread messages, DMs, and mentions.
"""

from datetime import datetime

from integrations.base import BaseIntegration
from assistant.priority import PriorityItem, PriorityEngine
from config import SLACK_BOT_TOKEN, SLACK_USER_TOKEN


class SlackIntegration(BaseIntegration):
    name = "slack"

    def __init__(self):
        self.client = None
        self.connected = False
        self._scorer = PriorityEngine()
        self._user_id = None

    async def connect(self) -> bool:
        if not SLACK_BOT_TOKEN:
            print("[Slack] No bot token configured")
            return False

        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError

            self.client = WebClient(token=SLACK_BOT_TOKEN)
            auth = self.client.auth_test()
            self._user_id = auth["user_id"]
            self.connected = True
            return True

        except Exception as e:
            print(f"[Slack] Connection failed: {e}")
            self.connected = False
            return False

    async def fetch_items(self) -> list[PriorityItem]:
        if not self.connected or not self.client:
            return []

        items = []

        try:
            # Get conversations (channels + DMs) with unread messages
            conversations = self.client.users_conversations(
                types="im,mpim,public_channel,private_channel",
                limit=50,
            )

            for channel in conversations.get("channels", []):
                channel_id = channel["id"]
                is_dm = channel.get("is_im", False)
                channel_name = channel.get("name", "DM")

                if is_dm:
                    # Get DM partner name
                    try:
                        user_info = self.client.users_info(user=channel.get("user", ""))
                        channel_name = f"DM with {user_info['user']['real_name']}"
                    except Exception:
                        channel_name = "Direct Message"

                # Fetch recent messages
                try:
                    history = self.client.conversations_history(
                        channel=channel_id,
                        limit=5,
                    )

                    for msg in history.get("messages", []):
                        if msg.get("user") == self._user_id:
                            continue  # Skip own messages

                        text = msg.get("text", "")
                        is_mention = self._user_id in text if self._user_id else False
                        ts = float(msg.get("ts", 0))
                        date = datetime.fromtimestamp(ts) if ts else datetime.now()

                        # Only include recent messages (last 4 hours)
                        hours_old = (datetime.now() - date).total_seconds() / 3600
                        if hours_old > 4:
                            continue

                        urgency = self._scorer.score_slack_message(text, is_mention, is_dm, date)

                        # Only surface messages with meaningful urgency
                        if urgency >= 3:
                            # Get sender name
                            sender = "Unknown"
                            try:
                                user_info = self.client.users_info(user=msg.get("user", ""))
                                sender = user_info["user"]["real_name"]
                            except Exception:
                                pass

                            items.append(PriorityItem(
                                source="slack",
                                title=f"{sender} in {channel_name}",
                                detail=text[:300],
                                urgency=urgency,
                                timestamp=date,
                                link=f"slack://channel?team=&id={channel_id}",
                                tags=["slack", "dm" if is_dm else "channel"],
                            ))

                except Exception:
                    continue

        except Exception as e:
            print(f"[Slack] Fetch error: {e}")

        return items

    async def get_context_summary(self) -> str:
        if not self.connected:
            return "Slack: Not connected. Configure SLACK_BOT_TOKEN to enable."

        items = await self.fetch_items()
        if not items:
            return "Slack: No important unread messages."

        lines = [f"Slack: {len(items)} messages needing attention"]
        for item in sorted(items, key=lambda x: -x.urgency)[:10]:
            lines.append(f"  [{item.level}] {item.title}")
            lines.append(f"    {item.detail[:120]}")

        return "\n".join(lines)
