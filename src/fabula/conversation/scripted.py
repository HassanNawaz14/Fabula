"""Deterministic, persona-aware conversation used when live APIs are disabled."""

from __future__ import annotations

import random
import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from fabula.conversation.dto import PromptContext
from fabula.schemas import Clue, DiscoveryMethod, Mood


class _Intent(StrEnum):
    GREETING = "greeting"
    IDENTITY = "identity"
    STORY = "story"
    CASE = "case"
    ACCUSATION = "accusation"
    FAREWELL = "farewell"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ScriptedReply:
    text: str
    mood: Mood
    revealed_clue_ids: tuple[str, ...] = ()


_GREETINGS = (
    "Good to see you. I'm {name}; I'm {role} here.",
    "Hello there. {name}. I look after things as {role}.",
    "Morning to you. I'm {name}, {role}.",
)

_IDENTITY = (
    "I'm {name}. Around here I'm {role}. People would tell you I'm {traits}.",
    "The name is {name}. I'm {role}, and I like to think I'm {traits}.",
    "I'm {name}, {role}. {traits} — that's the short version.",
)

_STORY = (
    "For what it's worth: {backstory}",
    "There is not much to tell, but here it is: {backstory}",
    "Since you ask: {backstory}",
)

_CASE_WITH_CLUE = (
    "I have been thinking about that. {description}",
    "As {role}, I notice things. {description}",
    "I can tell you this much: {description}",
    "Between us — {description}",
)

_CASE_EMPTY = (
    "I've told you what I know. I don't want to guess beyond that.",
    "That is all I can say with a clear conscience.",
    "I wish I could help more, but I won't invent details.",
)

_ACCUSATION = (
    "That is a serious accusation. I won't pretend it doesn't sting.",
    "You can think what you like, but I have told you the truth.",
    "Careful. Accusing people without proof only makes noise.",
)

_FAREWELL = (
    "Take care. Come back if you think of the right question.",
    "I'll be here. Ask again if something else comes to mind.",
    "Good luck. Keep your eyes open.",
)

_UNKNOWN = (
    "I'm not sure I follow. Ask me about what I saw or what I know about that day.",
    "You've lost me. Try asking plainly about the matter at hand.",
    "I don't have an answer to that. Ask me something about what happened.",
)


class ScriptedResponder:
    def __init__(self, seed: int = 0) -> None:
        self._seed = seed

    def reply(
        self,
        context: PromptContext,
        *,
        clues: Sequence[Clue] = (),
        discovered_clue_ids: frozenset[str] = frozenset(),
        turn_index: int = 0,
    ) -> ScriptedReply:
        intent = _detect_intent(context.player_input)
        eligible = _eligible_clues(
            context.identity.id,
            clues,
            discovered_clue_ids,
        )
        if intent is _Intent.CASE and eligible:
            clue = eligible[0]
            rng = self._rng(context, intent, turn_index)
            return ScriptedReply(
                text=_clip(
                    rng.choice(_CASE_WITH_CLUE).format(
                        description=clue.description,
                        role=context.identity.role,
                    )
                ),
                mood=Mood.NEUTRAL,
                revealed_clue_ids=(clue.id,),
            )

        rng = self._rng(context, intent, turn_index)
        if intent is _Intent.GREETING:
            text = rng.choice(_GREETINGS).format(
                name=context.identity.name,
                role=context.identity.role,
            )
            mood = Mood.FRIENDLY
        elif intent is _Intent.IDENTITY:
            text = rng.choice(_IDENTITY).format(
                name=context.identity.name,
                role=context.identity.role,
                traits=_trait_phrase(context),
            )
            mood = Mood.NEUTRAL
        elif intent is _Intent.STORY:
            text = rng.choice(_STORY).format(backstory=_short_backstory(context))
            mood = Mood.NEUTRAL
        elif intent is _Intent.CASE:
            text = rng.choice(_CASE_EMPTY)
            mood = Mood.NEUTRAL
        elif intent is _Intent.ACCUSATION:
            text = rng.choice(_ACCUSATION)
            mood = Mood.ANGRY
        elif intent is _Intent.FAREWELL:
            text = rng.choice(_FAREWELL)
            mood = Mood.FRIENDLY
        else:
            text = rng.choice(_UNKNOWN)
            mood = Mood.NEUTRAL
        return ScriptedReply(text=_clip(text), mood=mood)

    def _rng(self, context: PromptContext, intent: _Intent, turn_index: int) -> random.Random:
        return random.Random(f"{self._seed}:{context.identity.id}:{turn_index}:{intent.value}")


def _trait_phrase(context: PromptContext) -> str:
    traits = [trait for trait in context.identity.traits if trait.strip()]
    if not traits:
        return "myself"
    if len(traits) == 1:
        return traits[0]
    return f"{traits[0]} and {traits[1]}"


def _short_backstory(context: PromptContext) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", context.identity.backstory.strip())
    return sentences[0] if sentences and sentences[0] else "I keep to myself."


def _clip(text: str) -> str:
    return text if len(text) <= 4000 else text[:3997] + "..."


def _eligible_clues(
    npc_id: str,
    clues: Sequence[Clue],
    discovered_clue_ids: frozenset[str],
) -> tuple[Clue, ...]:
    return tuple(
        clue
        for clue in clues
        if clue.discovery is DiscoveryMethod.NPC_REVEAL
        and clue.revealed_by_npc == npc_id
        and clue.id not in discovered_clue_ids
        and set(clue.requires) <= discovered_clue_ids
    )


def _detect_intent(text: str) -> _Intent:
    lowered = text.lower()
    words = set(re.sub(r"[^a-z0-9]+", " ", lowered).split())

    if any(
        phrase in lowered
        for phrase in (
            "you did it",
            "you stole",
            "you killed",
            "you are the culprit",
            "you're the culprit",
            "confess",
            "liar",
            "guilty",
        )
    ):
        return _Intent.ACCUSATION
    if words & {"hello", "hi", "hey", "greetings"} or "good morning" in lowered:
        return _Intent.GREETING
    if words & {"bye", "goodbye", "farewell"} or "see you" in lowered:
        return _Intent.FAREWELL
    if any(
        phrase in lowered
        for phrase in (
            "backstory",
            "your story",
            "tell me about yourself",
            "where are you from",
            "your past",
        )
    ):
        return _Intent.STORY
    if any(
        phrase in lowered
        for phrase in ("who are you", "your name", "about yourself", "what do you do")
    ):
        return _Intent.IDENTITY
    if words & {
        "help",
        "clue",
        "saw",
        "see",
        "know",
        "knows",
        "heard",
        "notice",
        "noticed",
        "happened",
        "missing",
        "stolen",
        "murder",
        "crime",
        "alibi",
        "suspect",
        "investigate",
        "tell",
        "evidence",
        "anything",
    }:
        return _Intent.CASE
    return _Intent.UNKNOWN
