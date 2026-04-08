"""
Integration Registry
--------------------
Manages all integration adapters. Provides auto-discovery,
concurrent fetching, and a clean interface for the brain
and priority engine.
"""

import asyncio
from integrations.base import BaseIntegration
from assistant.priority import PriorityItem


class IntegrationRegistry:
    """Central manager for all service integrations."""

    def __init__(self):
        self._adapters: dict[str, BaseIntegration] = {}

    def register(self, adapter: BaseIntegration):
        """Register an integration adapter."""
        self._adapters[adapter.name] = adapter

    def unregister(self, name: str):
        """Remove an integration adapter."""
        self._adapters.pop(name, None)

    def get(self, name: str) -> BaseIntegration | None:
        """Get a specific adapter by name."""
        return self._adapters.get(name)

    def list_all(self) -> dict[str, BaseIntegration]:
        """Return all registered adapters."""
        return dict(self._adapters)

    def list_active(self) -> list[str]:
        """Return names of connected integrations."""
        return [name for name, adapter in self._adapters.items() if adapter.connected]

    def list_status(self) -> dict[str, dict]:
        """Return status of all integrations."""
        return {name: adapter.status() for name, adapter in self._adapters.items()}

    async def connect_all(self):
        """Attempt to connect all registered integrations."""
        results = {}
        for name, adapter in self._adapters.items():
            try:
                success = await adapter.connect()
                results[name] = success
            except Exception as e:
                results[name] = False
                print(f"  [OFFLINE] {name} - {e}")
        return results

    async def fetch_all_items(self) -> list[PriorityItem]:
        """Fetch items from all connected integrations concurrently."""
        tasks = []
        for name, adapter in self._adapters.items():
            if adapter.connected:
                tasks.append(self._safe_fetch(name, adapter))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks)
        all_items = []
        for items in results:
            all_items.extend(items)
        return all_items

    async def get_all_context(self) -> dict[str, str]:
        """Get context summaries from all connected integrations."""
        context = {}
        for name, adapter in self._adapters.items():
            if adapter.connected:
                try:
                    context[name] = await adapter.get_context_summary()
                except Exception as e:
                    context[name] = f"Error: {e}"
        return context

    async def _safe_fetch(self, name: str, adapter: BaseIntegration) -> list[PriorityItem]:
        """Fetch items with error handling."""
        try:
            return await adapter.fetch_items()
        except Exception as e:
            print(f"[Registry] Error fetching from {name}: {e}")
            return []
