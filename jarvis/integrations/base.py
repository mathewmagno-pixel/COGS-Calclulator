"""
Base Integration Interface
--------------------------
All integrations implement this common interface so the priority engine
and brain can interact with them uniformly.
"""

from abc import ABC, abstractmethod
from assistant.priority import PriorityItem


class BaseIntegration(ABC):
    """Abstract base class for all service integrations."""

    name: str = "base"
    connected: bool = False

    @abstractmethod
    async def connect(self) -> bool:
        """Initialize connection to the service. Returns True if successful."""
        ...

    @abstractmethod
    async def fetch_items(self) -> list[PriorityItem]:
        """Fetch actionable items from the service."""
        ...

    @abstractmethod
    async def get_context_summary(self) -> str:
        """Return a text summary of current state for the AI brain."""
        ...

    async def disconnect(self):
        """Clean up connections."""
        self.connected = False

    def status(self) -> dict:
        return {"name": self.name, "connected": self.connected}
