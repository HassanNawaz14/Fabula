"""Runtime conversation errors."""

from __future__ import annotations


class ConversationError(Exception):
    """Base error for the conversation subsystem."""


class ConversationSetupError(ConversationError):
    """Configuration prevents the requested conversation mode from starting."""


class NpcFileError(ConversationError, ValueError):
    """An NPC file is missing, unsafe, or internally inconsistent."""


class ProviderError(ConversationError):
    """A live provider failed or returned an unusable response."""


class ProviderTimeout(ProviderError):
    """A live provider exceeded its configured timeout."""
