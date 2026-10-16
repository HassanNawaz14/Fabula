from fabula.schemas.enums import LocationType

TOWN_NAMES = [
    "Willowbrook",
    "Littleford",
    "Ashgrove",
    "Dunmore",
    "Puddlewick",
    "Kingshollow",
    "Brindlebay",
    "Oakenford",
    "Merridale",
    "Coldharbor",
]

FIRST_NAMES = [
    "Mira",
    "Ravi",
    "Tomas",
    "Elsie",
    "Nadia",
    "Piotr",
    "Sana",
    "Gus",
    "Ivy",
    "Omar",
    "Bess",
    "Kofi",
    "Lena",
    "Dario",
    "Fenn",
    "Hana",
]

ROLES = [
    "market vendor",
    "librarian",
    "coach driver",
    "baker",
    "carpenter",
    "herbalist",
    "night watchman",
    "tea-house keeper",
    "stable hand",
    "schoolteacher",
    "fishmonger",
    "clocksmith",
]

TRAITS = [
    "observant",
    "guarded",
    "chatty",
    "nervous",
    "stubborn",
    "kind",
    "sly",
    "earnest",
    "gloomy",
    "jolly",
    "impatient",
    "methodical",
]

SPEECH_STYLES = [
    "short, direct sentences",
    "warm but rambling",
    "formal and precise",
    "dry humour",
    "quiet, rarely finishes thoughts",
    "quick and peppered with questions",
]

BACKSTORIES = [
    "Grew up in {town} and never left.",
    "Came to {town} a few years ago and stayed for the quiet.",
    "Inherited their trade from a relative in {town}.",
    "Runs their small business debts like a ledger.",
    "Known in {town} for always being early.",
]

GOALS = [
    "keep their job",
    "protect their reputation",
    "help the town",
    "earn enough for a fresh start",
    "stay out of other people's business",
    "prove someone a wrongdoer wrong",
]

ATTITUDES = [
    "polite but guarded",
    "friendly and eager to help",
    "curious about the player",
    "wary of strangers",
    "tired and a little short-tempered",
]

RELATIONSHIPS = [
    "friend",
    "rival",
    "sibling",
    "employer",
    "owes a favour to",
    "argues with regularly",
]

LOCATION_PROFILES: dict[LocationType, tuple[list[str], list[str]]] = {
    LocationType.MARKET: (
        ["Saffron Market", "Harvest Market", "Riverside Market"],
        [
            "A busy square of stalls and shouting vendors.",
            "Canvas awnings, crates of fruit, and gossip in the air.",
        ],
    ),
    LocationType.LIBRARY: (
        ["Old Library", "Town Library", "Reading House"],
        [
            "Shelves floor to ceiling and the smell of old paper.",
            "A quiet hall where whispers feel loud.",
        ],
    ),
    LocationType.CAFE: (
        ["Copper Kettle Cafe", "The Steaming Cup", "Little Cafe"],
        [
            "Small tables, strong tea, and the town's rumour mill.",
            "Warm light and the clink of cups.",
        ],
    ),
    LocationType.PARK: (
        ["Town Park", "Willow Green", "Elder Park"],
        [
            "A green square with benches and a tired old tree.",
            "Paths worn into the grass by generations of walkers.",
        ],
    ),
    LocationType.PARKING: (
        ["Town Parking Lot", "Coach Yard", "Old Parking Lot"],
        [
            "An open lot with flickering lamps and oil stains.",
            "Rows of empty spaces, a cart or two, and cracked paint.",
        ],
    ),
    LocationType.RESIDENCE: (
        ["Quiet Residence", "Old Cottage", "Lane House"],
        [
            "A small private house on a quiet lane.",
            "Curtains drawn, a swept step, a locked side door.",
        ],
    ),
}

HERRING_ACTS = [
    "has been skipping their night watch rounds",
    "secretly sells extra bread from the bakery",
    "hid a stack of overdue library books at home",
    "pretends to work when the coach is late",
    "spreads a rumour about the herbalist",
    "pockets a little coin from the tea house",
]

WITNESS_LINES = [
    "I saw someone hurry away from the {place} around that time, but I could not see their face.",
    "I passed the {place} and noticed something felt wrong, though I cannot say what.",
    "I was near the {place} and heard raised voices that stopped suddenly.",
]

ALIBI_LINES = [
    "I was at the {place} around that time, ask anyone.",
    "I spent that stretch of the day at the {place}, plain as that.",
]

RUMOUR_LINES = [
    "People say the {target} was trouble waiting to happen.",
    "I heard the {target} had been discussed at every stall that morning.",
    "Someone told me the {target} was involved in old town business.",
]

TRACE_LINES = [
    "I left in a hurry and knocked over a crate near the {place}.",
    "My footprints are probably still in the dust by the {place}.",
    "I dropped a button from my coat near the {place}.",
]
