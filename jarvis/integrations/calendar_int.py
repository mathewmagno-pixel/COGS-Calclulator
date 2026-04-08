"""
Google Calendar Integration
----------------------------
Fetches upcoming events and scores them by proximity.
"""

from datetime import datetime, timedelta
from pathlib import Path

from integrations.base import BaseIntegration
from assistant.priority import PriorityItem, PriorityEngine
from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_TOKEN_FILE


class CalendarIntegration(BaseIntegration):
    name = "calendar"

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

            SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
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

            self.service = build("calendar", "v3", credentials=creds)
            self.connected = True
            return True

        except Exception as e:
            print(f"[Calendar] Connection failed: {e}")
            self.connected = False
            return False

    async def fetch_items(self) -> list[PriorityItem]:
        if not self.connected or not self.service:
            return []

        try:
            now = datetime.utcnow()
            time_min = now.isoformat() + "Z"
            time_max = (now + timedelta(hours=24)).isoformat() + "Z"

            events_result = self.service.events().list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=20,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = events_result.get("items", [])
            items = []

            for event in events:
                start_str = event["start"].get("dateTime", event["start"].get("date"))
                summary = event.get("summary", "Untitled Event")

                try:
                    from dateutil.parser import parse
                    start = parse(start_str).replace(tzinfo=None)
                except Exception:
                    start = datetime.now()

                urgency = self._scorer.score_calendar_event(summary, start)

                attendees = event.get("attendees", [])
                attendee_names = [a.get("email", "") for a in attendees[:5]]
                detail = f"Time: {start.strftime('%I:%M %p')}"
                if attendee_names:
                    detail += f" | With: {', '.join(attendee_names)}"
                if event.get("location"):
                    detail += f" | Location: {event['location']}"
                if event.get("hangoutLink"):
                    detail += f" | Video: {event['hangoutLink']}"

                items.append(PriorityItem(
                    source="calendar",
                    title=summary,
                    detail=detail,
                    urgency=urgency,
                    timestamp=start,
                    link=event.get("htmlLink", ""),
                    tags=["meeting", "calendar"],
                ))

            return items

        except Exception as e:
            print(f"[Calendar] Fetch error: {e}")
            return []

    async def get_context_summary(self) -> str:
        if not self.connected:
            return "Calendar: Not connected. Configure Google OAuth credentials to enable."

        items = await self.fetch_items()
        if not items:
            return "Calendar: No upcoming events in the next 24 hours."

        lines = [f"Calendar: {len(items)} upcoming events today"]
        for item in items[:10]:
            lines.append(f"  [{item.level}] {item.title}")
            lines.append(f"    {item.detail}")

        return "\n".join(lines)
