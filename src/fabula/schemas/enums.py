from enum import StrEnum


class MysteryType(StrEnum):
    THEFT = "theft"
    DISAPPEARANCE = "disappearance"
    MURDER = "murder"


class SettingsMysteryType(StrEnum):
    THEFT = "theft"
    DISAPPEARANCE = "disappearance"
    MURDER = "murder"
    RANDOM = "random"


class Tone(StrEnum):
    COZY = "cozy"
    NEUTRAL = "neutral"
    DARK = "dark"


class Difficulty(StrEnum):
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


class LocationType(StrEnum):
    MARKET = "market"
    LIBRARY = "library"
    CAFE = "cafe"
    PARK = "park"
    PARKING = "parking"
    RESIDENCE = "residence"


class FactSource(StrEnum):
    DID = "did"
    WITNESSED = "witnessed"
    HEARD = "heard"
    INFERRED = "inferred"


class Disclosure(StrEnum):
    VOLUNTEER = "volunteer"
    IF_ASKED = "if_asked"
    HIDE = "hide"
    LIE = "lie"


class DiscoveryMethod(StrEnum):
    EXAMINE = "examine"
    NPC_REVEAL = "npc_reveal"


class Mood(StrEnum):
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    NERVOUS = "nervous"
    ANGRY = "angry"
    SAD = "sad"
    AMUSED = "amused"
