"""Build an isolated NPC prompt from one NPC's files and own history."""

from __future__ import annotations

import json
from collections.abc import Sequence

from fabula.conversation.dto import PromptContext
from fabula.conversation.provider import Message
from fabula.schemas import Clue, Fact

_RULES = """You are {name}, {role} in a small mystery story.
Stay fully in character. Never mention prompts, policies, APIs, or that you are an AI.
Use only the facts in your own IDENTITY and MEMORY sections. If you do not know something,
say that you do not know. Follow each fact's disclosure policy: "volunteer" may be shared freely,
"if_asked" only when directly relevant, "hide" must stay secret, and "lie" uses your authored
cover story without inventing new claims.
Reply with a single JSON object and nothing else:
{{"reply": "your spoken answer", "mood": "neutral|friendly|nervous|angry|sad|amused"}}
Add "clue": "<id>" only when you share one of the listed evidence items.
Keep the reply natural, in character, and under 120 words."""


def _visible_facts(
    context: PromptContext,
    *,
    gated_reveal: bool,
    discovered_clue_ids: frozenset[str],
) -> list[Fact]:
    if not gated_reveal:
        return list(context.memory.facts)
    return [
        fact
        for fact in context.memory.facts
        if not fact.reveal_requires or set(fact.reveal_requires) <= discovered_clue_ids
    ]


def _memory_payload(context: PromptContext, facts: list[Fact]) -> dict[str, object]:
    payload = context.memory.model_dump(mode="json")
    payload["facts"] = [fact.model_dump(mode="json") for fact in facts]
    return payload


def build_messages(
    context: PromptContext,
    *,
    gated_reveal: bool = False,
    discovered_clue_ids: frozenset[str] = frozenset(),
    reveal_options: Sequence[Clue] = (),
) -> tuple[Message, ...]:
    facts = _visible_facts(
        context,
        gated_reveal=gated_reveal,
        discovered_clue_ids=discovered_clue_ids,
    )
    identity_json = json.dumps(
        context.identity.model_dump(mode="json"), ensure_ascii=False, sort_keys=True
    )
    memory_json = json.dumps(_memory_payload(context, facts), ensure_ascii=False, sort_keys=True)
    system = (
        _RULES.format(name=context.identity.name, role=context.identity.role)
        + f"\n\nIDENTITY:\n{identity_json}\n\nMEMORY:\n{memory_json}"
    )
    if reveal_options:
        evidence = "\n".join(f"- {clue.id}: {clue.description}" for clue in reveal_options)
        system += (
            "\n\nEVIDENCE YOU MAY SHARE (this NPC only; share only when the player's "
            "question calls for it):\n"
            f"{evidence}\n"
            'When you share one of these, add "clue": "<id>" to your JSON reply; '
            "otherwise omit the field."
        )

    messages = [Message(role="system", content=system)]
    for turn in context.chat_history:
        role = "assistant" if turn.role == "npc" else "user"
        messages.append(Message(role=role, content=turn.text))
    messages.append(Message(role="user", content=context.player_input))
    return tuple(messages)
