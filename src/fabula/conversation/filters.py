"""Input safety filter and deterministic output leak filter."""

from __future__ import annotations

import re
from dataclasses import dataclass

from fabula.schemas import Disclosure, Memory

_PROTECTED_DISCLOSURES = frozenset({Disclosure.HIDE, Disclosure.LIE})

_BLOCKED_INPUT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "self_harm",
        re.compile(
            r"\b(?:kill myself|killing myself|suicide|self[-\s]?harm|cut myself|end my life)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "sexual",
        re.compile(
            r"\b(?:sex|sexual|nudes?|porn(?:ography)?|erotic|send nudes|"
            r"sexual favors?|explicit sex|have sex with me)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "hate",
        re.compile(
            r"\b(?:hate all|hate those|hate you|hate speech|racial slurs?|slurs?|"
            r"inferior race|subhuman|should be exterminated|exterminate|"
            r"go back to your country)\b",
            re.IGNORECASE,
        ),
    ),
)


@dataclass(frozen=True)
class InputCheck:
    blocked: bool
    category: str | None = None


@dataclass(frozen=True)
class LeakMatch:
    matched_fact_ids: tuple[str, ...]

    @property
    def blocked(self) -> bool:
        return bool(self.matched_fact_ids)


def check_player_input(text: str) -> InputCheck:
    for category, pattern in _BLOCKED_INPUT_PATTERNS:
        if pattern.search(text):
            return InputCheck(blocked=True, category=category)
    return InputCheck(blocked=False)


def _normalize(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def find_leaked_facts(reply: str, memory: Memory) -> LeakMatch:
    normalized_reply = _normalize(reply)
    matched = tuple(
        fact.id
        for fact in memory.facts
        if fact.disclosure in _PROTECTED_DISCLOSURES
        and _normalize(fact.what)
        and _normalize(fact.what) in normalized_reply
    )
    return LeakMatch(matched_fact_ids=matched)
