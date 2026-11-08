"""Conversation service: modes, input safety, providers, parsing, and fallbacks."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import httpx

from fabula.conversation.config import (
    ApiKeys,
    ConversationConfig,
    ConversationMode,
    load_api_keys,
)
from fabula.conversation.dto import PromptContext
from fabula.conversation.errors import (
    ConversationSetupError,
    ProviderError,
    ProviderTimeout,
)
from fabula.conversation.filters import check_player_input, find_leaked_facts
from fabula.conversation.prompt_builder import build_messages
from fabula.conversation.provider import ChatProvider, ProviderRequest
from fabula.conversation.providers import GeminiProvider, XaiProvider
from fabula.conversation.scripted import ScriptedReply, ScriptedResponder
from fabula.schemas import ChatTurn, Clue, Mood, NpcFiles


@dataclass(frozen=True)
class ConversationReply:
    text: str
    mood: Mood
    mode: ConversationMode
    provider: str | None
    scripted: bool
    fallback: bool
    input_blocked: bool = False
    leak_blocked: bool = False
    revealed_clue_ids: tuple[str, ...] = ()
    leak_filter: bool = False
    gated_reveal: bool = False


@dataclass(frozen=True)
class ConversationStatus:
    mode: ConversationMode
    provider: str | None
    reason: str
    tokens_used: int
    token_cap: int


@dataclass(frozen=True)
class ParsedReply:
    text: str
    mood: Mood


_FALLBACK_LINES = (
    '{name} pauses, then says, "Not now — give me a moment to think."',
    '{name} frowns. "I am sorry, I cannot find the right words just now."',
    '{name} looks away briefly. "Ask me again in a moment."',
)

_INPUT_BLOCKED = '{name} holds up a hand. "Let us keep this civil."'
_LEAK_DEFLECTION = (
    '{name} hesitates, then chooses their words carefully. "I would rather not get into that."'
)


def parse_npc_reply(raw: str) -> ParsedReply:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        reply = payload.get("reply")
        if isinstance(reply, str) and reply.strip():
            mood = Mood.NEUTRAL
            raw_mood = payload.get("mood")
            if isinstance(raw_mood, str):
                try:
                    mood = Mood(raw_mood)
                except ValueError:
                    mood = Mood.NEUTRAL
            return ParsedReply(text=_clip(reply.strip()), mood=mood)
        return ParsedReply(text="", mood=Mood.NEUTRAL)
    return ParsedReply(text=_clip(cleaned), mood=Mood.NEUTRAL)


def create_conversation_service(
    config: ConversationConfig,
    *,
    providers: Mapping[str, ChatProvider] | None = None,
    keys: ApiKeys | None = None,
    http_client: httpx.Client | None = None,
) -> ConversationService:
    responder = ScriptedResponder(config.scripted_seed)
    if config.mode is ConversationMode.SCRIPTED:
        return ConversationService(
            config,
            provider=None,
            scripted=True,
            reason="forced_scripted",
            responder=responder,
        )

    resolved_keys = (
        keys if keys is not None else (config.keys if config.keys.any() else load_api_keys())
    )
    available = _available_providers(config, providers, resolved_keys)
    if not available:
        if config.mode is ConversationMode.LIVE:
            raise ConversationSetupError(
                "live conversation requires GEMINI_API_KEY or XAI_API_KEY; "
                "use FABULA_CONVERSATION_MODE=scripted to play without keys"
            )
        return ConversationService(
            config,
            provider=None,
            scripted=True,
            reason="no_api_key",
            responder=responder,
        )

    if providers is not None:
        selected = config.provider if config.provider in available else available[0]
        provider = providers[selected]
    else:
        provider = _build_provider(config, available, resolved_keys, http_client)
    return ConversationService(
        config,
        provider=provider,
        scripted=False,
        reason="live",
        responder=responder,
    )


def _available_providers(
    config: ConversationConfig,
    providers: Mapping[str, ChatProvider] | None,
    keys: ApiKeys,
) -> tuple[str, ...]:
    if providers is not None:
        names = tuple(name for name in config.provider_order if name in providers)
        return names or tuple(providers)
    return tuple(name for name in config.provider_order if keys.for_provider(name))


def _build_provider(
    config: ConversationConfig,
    available: tuple[str, ...],
    keys: ApiKeys,
    http_client: httpx.Client | None,
) -> ChatProvider:
    if config.provider in available:
        selected = config.provider
    else:
        selected = available[0]
    if selected == "gemini":
        key = keys.gemini
        if not key:
            raise ConversationSetupError("Gemini provider is unavailable without GEMINI_API_KEY")
        return GeminiProvider(
            key,
            config.gemini_model,
            timeout_seconds=config.timeout_seconds,
            client=http_client,
        )
    if selected == "xai":
        key = keys.xai
        if not key:
            raise ConversationSetupError("xAI provider is unavailable without XAI_API_KEY")
        return XaiProvider(
            key,
            config.xai_model,
            timeout_seconds=config.timeout_seconds,
            client=http_client,
        )
    raise ConversationSetupError(f"unknown conversation provider {selected!r}")


class ConversationService:
    def __init__(
        self,
        config: ConversationConfig,
        provider: ChatProvider | None,
        *,
        scripted: bool,
        reason: str,
        responder: ScriptedResponder | None = None,
    ) -> None:
        if config.token_cap < 0:
            raise ValueError("token_cap must not be negative")
        if config.max_history_messages < 1:
            raise ValueError("max_history_messages must be at least 1")
        self.config = config
        self._provider = provider
        self._scripted = scripted
        self._reason = reason
        self._responder = (
            responder if responder is not None else ScriptedResponder(config.scripted_seed)
        )
        self._history: dict[str, list[ChatTurn]] = {}
        self._tokens_used = 0

    @property
    def mode(self) -> ConversationMode:
        return ConversationMode.SCRIPTED if self._scripted else ConversationMode.LIVE

    @property
    def status(self) -> ConversationStatus:
        return ConversationStatus(
            mode=self.mode,
            provider=None if self._provider is None else self._provider.name,
            reason=self._reason,
            tokens_used=self._tokens_used,
            token_cap=self.config.token_cap,
        )

    @property
    def tokens_used(self) -> int:
        return self._tokens_used

    def close(self) -> None:
        close = getattr(self._provider, "close", None)
        if callable(close):
            close()

    def history_for(self, npc_id: str) -> tuple[ChatTurn, ...]:
        return tuple(self._history.get(npc_id, ()))

    def reset_history(self, npc_id: str | None = None) -> None:
        if npc_id is None:
            self._history.clear()
        else:
            self._history.pop(npc_id, None)

    def reply(
        self,
        files: NpcFiles,
        player_input: str,
        *,
        discovered_clue_ids: frozenset[str] = frozenset(),
        clues: Sequence[Clue] = (),
    ) -> ConversationReply:
        identity = files.identity
        memory = files.memory
        if identity.id != memory.npc_id:
            raise ValueError("NPC identity and memory do not belong together")
        text = player_input.strip()
        if not text:
            raise ValueError("player input must not be empty")

        blocked = check_player_input(text)
        if blocked.blocked:
            return ConversationReply(
                text=_INPUT_BLOCKED.format(name=identity.name),
                mood=Mood.NEUTRAL,
                mode=self.mode,
                provider=None if self._provider is None else self._provider.name,
                scripted=self._scripted,
                fallback=False,
                input_blocked=True,
                leak_filter=self.config.leak_filter,
                gated_reveal=self.config.gated_reveal,
            )

        history = tuple(self._history.get(identity.id, ()))
        context = PromptContext(
            identity=identity,
            memory=memory,
            chat_history=history,
            player_input=text,
        )

        if self._scripted:
            scripted = self._responder.reply(
                context,
                clues=clues,
                discovered_clue_ids=discovered_clue_ids,
                turn_index=len(history),
            )
            self._record(identity.id, text, scripted.text)
            return self._scripted_result(scripted, identity.name)

        if self._provider is None:
            raise ConversationSetupError("live mode requires a provider")
        if self._tokens_used >= self.config.token_cap:
            return self._fallback(identity.id, identity.name, text, "token_cap")

        messages = build_messages(
            context,
            gated_reveal=self.config.gated_reveal,
            discovered_clue_ids=discovered_clue_ids,
        )
        request = ProviderRequest(
            messages=messages,
            model=self._provider.model,
            max_output_tokens=self.config.max_output_tokens,
            temperature=self.config.temperature,
        )
        try:
            response = self._provider.complete(request)
        except (ProviderTimeout, ProviderError):
            return self._fallback(identity.id, identity.name, text, "provider_error")

        if not response.text.strip():
            return self._fallback(identity.id, identity.name, text, "empty_reply")

        self._tokens_used += response.total_tokens or _estimate_tokens(request, response.text)
        parsed = parse_npc_reply(response.text)
        if not parsed.text:
            return self._fallback(identity.id, identity.name, text, "empty_reply")

        leak_blocked = False
        final_text = parsed.text
        if self.config.leak_filter:
            match = find_leaked_facts(parsed.text, memory)
            if match.blocked:
                final_text = _LEAK_DEFLECTION.format(name=identity.name)
                leak_blocked = True

        self._record(identity.id, text, final_text)
        return ConversationReply(
            text=final_text,
            mood=parsed.mood,
            mode=ConversationMode.LIVE,
            provider=self._provider.name,
            scripted=False,
            fallback=False,
            leak_blocked=leak_blocked,
            leak_filter=self.config.leak_filter,
            gated_reveal=self.config.gated_reveal,
        )

    def _scripted_result(self, scripted: ScriptedReply, name: str) -> ConversationReply:
        return ConversationReply(
            text=_clip(scripted.text),
            mood=scripted.mood,
            mode=ConversationMode.SCRIPTED,
            provider=None,
            scripted=True,
            fallback=False,
            revealed_clue_ids=scripted.revealed_clue_ids,
            leak_filter=self.config.leak_filter,
            gated_reveal=self.config.gated_reveal,
        )

    def _fallback(
        self, npc_id: str, name: str, player_input: str, reason: str
    ) -> ConversationReply:
        index = (len(self._history.get(npc_id, ())) + len(reason)) % len(_FALLBACK_LINES)
        text = _FALLBACK_LINES[index].format(name=name)
        self._record(npc_id, player_input, text)
        return ConversationReply(
            text=text,
            mood=Mood.NEUTRAL,
            mode=self.mode,
            provider=None if self._provider is None else self._provider.name,
            scripted=self._scripted,
            fallback=True,
            leak_filter=self.config.leak_filter,
            gated_reveal=self.config.gated_reveal,
        )

    def _record(self, npc_id: str, player_text: str, npc_text: str) -> None:
        history = self._history.setdefault(npc_id, [])
        history.append(ChatTurn(role="player", text=_clip(player_text)))
        history.append(ChatTurn(role="npc", text=_clip(npc_text)))
        if len(history) > self.config.max_history_messages:
            del history[: len(history) - self.config.max_history_messages]


def _clip(text: str) -> str:
    return text if len(text) <= 4000 else text[:3997] + "..."


def _estimate_tokens(request: ProviderRequest, reply: str) -> int:
    prompt_chars = sum(len(message.content) for message in request.messages)
    return max(1, (prompt_chars + len(reply)) // 4)
