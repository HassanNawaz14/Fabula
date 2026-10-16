from typing import Literal

from pydantic import Field, model_validator

from fabula.schemas.npc import Identity, Memory
from fabula.schemas.world import StrictModel, TextStr


class ChatTurn(StrictModel):
    role: Literal["player", "npc"]
    text: TextStr


class NpcPromptInput(StrictModel):
    identity: Identity
    memory: Memory
    chat_history: list[ChatTurn] = Field(default_factory=list)
    player_input: TextStr

    @model_validator(mode="after")
    def memory_matches_identity(self) -> "NpcPromptInput":
        if self.memory.npc_id != self.identity.id:
            raise ValueError("prompt memory must belong to the prompt identity")
        return self
