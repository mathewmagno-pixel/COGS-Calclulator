"""
Gmail Integration
-----------------
Connects to Gmail via the Google API to fetch recent emails,
score their urgency, and surface important messages.
"""

import base64
from datetime import datetime
from pathlib import Path

from integrations.base import BaseIntegration
from assistant.priority import PriorityItem, PriorityEngine
from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_TOKEN_FILE, GMAIL_MAX_RESULTS


class GmailIntegration(BaseIntegration):
    name = "gmail"

    def __init__(self):
        self.service = None
        self.connected = False
        self._scorer = PriorityEngine()

    async def connect(self) -> bool:
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build

            SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
            creds = None
            token_path = Path(GOOGLE_TOKEN_FILE)

            if token_path.exists():
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        GOOGLE_CREDENTIALS_FILE, SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                token_path.write_text(creds.to_json())

            self.service = build("gmail", "v1", credentials=creds)
            self.connected = True
            return True

        except Exception as e:
            print(f"[Gmail] Connection failed: {e}")
            self.connected = False
            return False

    async def fetch_items(self) -> list[PriorityItem]:
        if not self.connected or not self.service:
            return []

        try:
            results = self.service.users().messages().list(
                userId="me",
                maxResults=GMAIL_MAX_RESULTS,
                q="is:unread in:inbox",
            ).execute()

            messages = results.get("messages", [])
            items = []

            for msg_meta in messages:
                msg = self.service.users().messages().get(
                    userId="me", id=msg_meta["id"], format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                ).execute()

                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                subject = headers.get("Subject", "(no subject)")
                sender = headers.get("From", "unknown")
                snippet = msg.get("snippet", "")
                date_str = headers.get("Date", "")

                try:
                    # Parse various date formats
                    from email.utils import parsedate_to_datetime
                    date = parsedate_to_datetime(date_str)
                    date = date.replace(tzinfo=None)
                except Exception:
                    date = datetime.now()

                urgency = self._scorer.score_email(subject, sender, snippet, date)

                items.append(PriorityItem(
                    source="gmail",
                    title=f"Email from {sender.split('<')[0].strip()}: {subject}",
                    detail=snippet,
                    urgency=urgency,
                    timestamp=date,
                    link=f"https://mail.google.com/mail/u/0/#inbox/{msg_meta['id']}",
                    tags=["email", "unread"],
                ))

            return items

        except Exception as e:
            print(f"[Gmail] Fetch error: {e}")
            return []

    async def get_context_summary(self) -> str:
        if not self.connected:
            return "Gmail: Not connected. Configure Google OAuth credentials to enable."

        items = await self.fetch_items()
        if not items:
            return "Gmail: No unread emails in inbox."

        lines = [f"Gmail: {len(items)} unread emails"]
        for item in sorted(items, key=lambda x: -x.urgency)[:10]:
            lines.append(f"  [{item.level}] {item.title}")
            if item.detail:
                lines.append(f"    Preview: {item.detail[:100]}")

        return "\n".join(lines)
