from fabula.schemas.enums import LocationType

KEY = "theft"

TARGETS = [
    "silver locket",
    "leather ledger",
    "brass pocket watch",
    "box of rare tea",
    "silver money bowl",
    "antique hand mirror",
]

METHODS = [
    "slipped it into a coat pocket while the stall was busy",
    "hid it under a fruit crate and came back for it",
    "traded it for a cheap copy during the rush",
    "lifted it off the counter when the vendor turned away",
    "wrapped it in a scarf and walked out calmly",
    "swapped it with a lookalike from another stall",
    "convinced the owner it was already sold and left with it",
    "knocked over a display and took it in the confusion",
]

MOTIVES = [
    "pay off a growing debt",
    "fund a fresh start in another town",
    "cover a loss they were blamed for",
    "prove they were smarter than the market folk",
    "help a sibling in secret trouble",
    "buy back a family heirloom of their own",
]

CRIME_LOCATION_PREF = [LocationType.MARKET, LocationType.PARKING, LocationType.LIBRARY]

TITLE_FMT = "The Stolen {target}"
INTRO_FMT = (
    "A {target} has gone missing from the {crime_place} in {town} this morning. "
    "Someone here knows more than they are saying."
)


def how_text(culprit_name: str, method: str, target: str, crime_place: str, minute: int) -> str:
    return (
        f"{culprit_name} {method} at the {crime_place} at minute {minute} — the {target} is gone."
    )


def why_text(motive: str) -> str:
    return f"They did it to {motive}."
