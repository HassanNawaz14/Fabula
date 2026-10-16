from fabula.schemas.enums import LocationType

KEY = "disappearance"

TARGETS = [
    "the night baker",
    "the old ferrymaster",
    "the travelling clocksmith",
    "the schoolteacher",
    "the herbalist's apprentice",
    "the retired coachman",
]

METHODS = [
    "lured them behind the sheds with a fake errand",
    "tricked them into leaving town on the wrong coach",
    "argued with them near the water and they never came back",
    "sent them a forged note that pulled them away at night",
    "hitched their cart to the wrong route on purpose",
    "spread a lie that forced them to run from the town",
]

MOTIVES = [
    "keep an old secret buried",
    "take over their small business",
    "hide a debt that was about to be exposed",
    "settle a grudge from years ago",
    "clear the way for a new job posting",
    "stop them from reporting a theft",
]

CRIME_LOCATION_PREF = [LocationType.PARKING, LocationType.PARK, LocationType.RESIDENCE]

TITLE_FMT = "The Vanishing of {target}"
INTRO_FMT = (
    "{target} has vanished from {town} overnight. "
    "Nobody saw them leave, and nobody will say what they know."
)


def how_text(culprit_name: str, method: str, target: str, crime_place: str, minute: int) -> str:
    return (
        f"{culprit_name} {method} at the {crime_place} "
        f"at minute {minute}, and {target} was never seen that day."
    )


def why_text(motive: str) -> str:
    return f"They did it to {motive}."
