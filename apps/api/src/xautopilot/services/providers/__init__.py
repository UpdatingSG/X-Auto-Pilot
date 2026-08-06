"""Platform provider abstractions — browser or API backends share one interface."""

from xautopilot.services.providers.base import (
    Discussion,
    EngagementMetrics,
    PlatformProvider,
    PublishPayload,
    PublishResult,
    Reply,
)
from xautopilot.services.providers.registry import get_provider, list_provider_names, register_provider

__all__ = [
    "Discussion",
    "EngagementMetrics",
    "PlatformProvider",
    "PublishPayload",
    "PublishResult",
    "Reply",
    "get_provider",
    "list_provider_names",
    "register_provider",
]
