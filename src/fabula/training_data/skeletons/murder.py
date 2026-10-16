from fabula.schemas.enums import LocationType

KEY = "murder"

TARGETS = [
    "the night watchman",
    "the grain merchant",
    "the landlord's clerk",
    "the dockside cook",
    "the retired judge",
    "the caravan leader",
]

METHODS = [
    "poisoned their evening tea",
    "loosened a beam they often leaned on",
    "sent them down the wrong road at night",
    "sabotaged their cart so it rolled at the hill",
    "left a rigged lamp to fill their room with smoke",
    "tricked them into a dangerous meeting place",
]

MOTIVES = [
    "stop an old letter from being read aloud",
    "inherit a small but useful sum",
    "silence a witness to an earlier crime",
    "end a feud that had gone on too long",
    "keep a stolen land deed hidden",
    "punish them for a public humiliation",
]

CRIME_LOCATION_PREF = [LocationType.RESIDENCE, LocationType.PARK, LocationType.PARKING]

TITLE_FMT = "Death at the {crime_place}"
INTRO_FMT = (
    "{target} was found dead in {town}, and the town insists it was an accident. "
    "It was not. Find out who did it."
)


def how_text(culprit_name: str, method: str, target: str, crime_place: str, minute: int) -> str:
    return (
        f"{culprit_name} {method} at the {crime_place} "
        f"at minute {minute}, and {target} died for it."
    )


def why_text(motive: str) -> str:
    return f"They did it to {motive}."
