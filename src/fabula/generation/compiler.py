"""Symbolic Blueprint Compiler & Solvability Verifier.

Compiles a Compact Blueprint DSL into Fabula's frozen v1 Pydantic Bundle,
enforcing spatial walkability, epistemic memory slicing, and solvability proofs.
The blueprint's culprit, cast, timeline, clues, and knowledge drive the case;
the compiler only fills structural gaps the schema requires.
"""

from __future__ import annotations

import random
import re

from fabula.generation.dsl import Blueprint
from fabula.schemas import (
    AccusationOptions,
    Bundle,
    Clue,
    CluesDocument,
    CoverStory,
    Crime,
    Difficulty,
    Disclosure,
    DiscoveryMethod,
    Fact,
    FactSource,
    Identity,
    Location,
    LocationType,
    Memory,
    MethodOption,
    MotiveOption,
    MysteryType,
    NpcFiles,
    NpcRosterEntry,
    Position,
    RedHerring,
    ScheduleEntry,
    Solution,
    TimelineEntry,
    TimeWindow,
    Tone,
    TruthDocument,
    WorldDocument,
    validate_bundle,
)
from fabula.training_data.skeletons import common, disappearance, murder, theft

CONTENT_MAP = {
    MysteryType.THEFT: theft,
    MysteryType.DISAPPEARANCE: disappearance,
    MysteryType.MURDER: murder,
}

_METHOD_POOL = [
    ("meth_skeleton_key", "Used a duplicate skeleton key to gain unauthorized entry."),
    ("meth_poison_vial", "Slipped a slow-acting poison tincture into beverage."),
    ("meth_distraction", "Created a staged commotion to slip past security unseen."),
    ("meth_forced_latch", "Pried open the window latch with a pocket tool."),
    ("meth_forgery", "Substituted the genuine item with an expert counterfeit."),
]

_MOTIVE_POOL = [
    ("mot_gambling_debt", "Desperate need to repay mounting debts to dangerous creditors."),
    ("mot_jealousy", "Bitter professional rivalry and envy of social standing."),
    ("mot_blackmail", "Silencing a blackmailer before dark secrets were exposed."),
    ("mot_inheritance", "Securing an estate bequest before the will could be altered."),
    ("mot_revenge", "Retribution for an ancient family grievance."),
]

_REVEAL_TYPES = ("document", "testimony", "witness", "rumor", "rumour", "letter", "memo", "note")


def _identifier(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_]+", "_", str(value).strip().lower()).strip("_")
    if not cleaned:
        return fallback
    if not cleaned[0].isalpha():
        cleaned = f"{fallback}_{cleaned}"
    return cleaned[:64]


def _fact_id(npc_id: str, suffix: str) -> str:
    return f"{npc_id[: 63 - len(suffix)]}_{suffix}"


def _coerce_enum(enum_type, value, fallback):
    try:
        return enum_type(str(value).strip().lower())
    except ValueError:
        return fallback


def _human(value: str) -> str:
    return str(value).replace("_", " ").strip()


def _sentence(value: str, fallback: str) -> str:
    text = _human(value).rstrip(".")
    if not text:
        return fallback
    return (text[:1].upper() + text[1:])[:399] + "."


class BlueprintCompiler:
    """Deterministic compiler from Blueprint DSL to frozen Pydantic Bundle."""

    def __init__(
        self,
        blueprint: Blueprint,
        seed: int | None = None,
        *,
        expected_type: MysteryType | str | None = None,
        expected_tone: Tone | str | None = None,
        expected_difficulty: Difficulty | str | None = None,
    ) -> None:
        self.blueprint = blueprint
        self.seed = seed if seed is not None else blueprint.seed
        self.rng = random.Random(f"fabula-blueprint-compiler:{self.seed}")

        # The caller's request wins over whatever the model wrote in the header.
        self.mystery_type = _coerce_enum(
            MysteryType, expected_type or blueprint.case_type, MysteryType.THEFT
        )
        self.content = CONTENT_MAP[self.mystery_type]
        self.tone = _coerce_enum(Tone, expected_tone or blueprint.tone, Tone.COZY)
        self.difficulty = _coerce_enum(
            Difficulty, expected_difficulty or blueprint.difficulty, Difficulty.NORMAL
        )
        self._loc_alias: dict[str, str] = {}

    # ------------------------------------------------------------------ locations

    def _location_type(self, raw: str) -> LocationType:
        hint = _identifier(raw, "loc")
        for location_type in LocationType:
            if location_type.value in hint:
                return location_type
        preferred = list(self.content.CRIME_LOCATION_PREF)
        return preferred[self.rng.randrange(len(preferred))]

    def _build_locations(self) -> tuple[list[Location], dict[str, str]]:
        """Build a connected 4-location town from every location the blueprint names."""
        referenced: list[str] = []
        raw_locations = [self.blueprint.crime.scene]
        raw_locations.extend(event.location for event in self.blueprint.timeline)
        raw_locations.extend(clue.location for clue in self.blueprint.clues)
        for raw in raw_locations:
            if not raw:
                continue
            loc_id = _identifier(raw, "loc")
            if loc_id not in referenced:
                referenced.append(loc_id)

        kept: list[tuple[str, LocationType]] = [
            (loc_id, self._location_type(loc_id)) for loc_id in referenced[:4]
        ]
        fillers = list(self.content.CRIME_LOCATION_PREF)
        fillers.extend(
            location_type for location_type in LocationType if location_type not in fillers
        )
        for location_type in fillers:
            if len(kept) >= 4:
                break
            loc_id = f"loc_{location_type.value}"
            if any(existing == loc_id for existing, _ in kept):
                continue
            kept.append((loc_id, location_type))

        kept_ids = [loc_id for loc_id, _ in kept]
        alias = {loc_id: loc_id for loc_id in kept_ids}
        for loc_id in referenced:
            if loc_id in alias:
                continue
            candidate = f"loc_{self._location_type(loc_id).value}"
            alias[loc_id] = candidate if candidate in kept_ids else kept_ids[0]

        locations: list[Location] = []
        for index, (loc_id, loc_type) in enumerate(kept):
            names, descriptions = common.LOCATION_PROFILES[loc_type]
            neighbors: list[str] = []
            if index > 0:
                neighbors.append(kept[index - 1][0])
                neighbors.append(kept[0][0])
            if index + 1 < len(kept):
                neighbors.append(kept[index + 1][0])
            elif index == 0 and len(kept) > 1:
                neighbors.append(kept[1][0])
            connections = [neighbor for neighbor in dict.fromkeys(neighbors) if neighbor != loc_id]
            locations.append(
                Location(
                    id=loc_id,
                    name=names[self.rng.randrange(len(names))],
                    type=loc_type,
                    description=descriptions[self.rng.randrange(len(descriptions))],
                    position=Position(x=index * 10, y=0),
                    connections=connections,
                    clue_spots=[],
                )
            )
        return locations, alias

    def _resolve_location(self, raw: str, location_ids: list[str]) -> str:
        loc_id = _identifier(raw, "loc")
        if loc_id in location_ids:
            return loc_id
        return self._loc_alias.get(loc_id, location_ids[0])

    # ------------------------------------------------------------------ cast

    def _build_npc_ids(self) -> list[str]:
        culprit_id = _identifier(self.blueprint.cast.culprit, "npc_01")
        npc_ids = [culprit_id]
        for raw in self.blueprint.cast.suspects:
            npc_id = _identifier(raw, "npc")
            if npc_id not in npc_ids:
                npc_ids.append(npc_id)
            if len(npc_ids) == 6:
                break
        filler = 1
        while len(npc_ids) < 5:
            candidate = f"npc_{filler:02d}"
            filler += 1
            if candidate not in npc_ids:
                npc_ids.append(candidate)
        return npc_ids

    def _build_timeline(
        self,
        npc_ids: list[str],
        location_ids: list[str],
        culprit_id: str,
        crime_scene_id: str,
        crime_minute: int,
    ) -> list[TimelineEntry]:
        entries: list[TimelineEntry] = []
        seen: set[tuple[str, int]] = set()

        def add(t: int, who: str, what: str, where: str) -> None:
            if who not in npc_ids:
                return
            t = max(0, min(10, int(t)))
            if (who, t) in seen:
                return
            seen.add((who, t))
            entries.append(
                TimelineEntry(
                    t=t,
                    who=who,
                    what=what or "Was seen going about their day.",
                    where=where,
                )
            )

        for event in self.blueprint.timeline:
            add(
                event.time,
                _identifier(event.actor, "npc"),
                event.action,
                self._resolve_location(event.location, location_ids),
            )
        if (culprit_id, crime_minute) not in seen:
            add(
                crime_minute,
                culprit_id,
                f"I {self._method_clause()} at the scene.",
                crime_scene_id,
            )
        for npc_id in npc_ids:
            if any(entry.who == npc_id for entry in entries):
                continue
            minute = self.rng.randrange(0, 11)
            while (npc_id, minute) in seen:
                minute = self.rng.randrange(0, 11)
            add(minute, npc_id, "Was seen going about their day.", self.rng.choice(location_ids))
        return sorted(entries, key=lambda entry: entry.t)

    def _build_roster_and_identities(
        self,
        npc_ids: list[str],
        location_ids: list[str],
        town: str,
        timeline: list[TimelineEntry],
        culprit_id: str,
        motive_clause: str,
    ) -> tuple[list[NpcRosterEntry], dict[str, Identity]]:
        names = self.rng.sample(common.FIRST_NAMES, k=len(npc_ids))
        by_npc: dict[str, list[TimelineEntry]] = {npc_id: [] for npc_id in npc_ids}
        for entry in timeline:
            if entry.who in by_npc:
                by_npc[entry.who].append(entry)

        roster: list[NpcRosterEntry] = []
        identities: dict[str, Identity] = {}
        for index, npc_id in enumerate(npc_ids):
            npc_entries = sorted(by_npc[npc_id], key=lambda entry: entry.t)[:3]
            schedule = [
                ScheduleEntry(at_minute=entry.t, location=entry.where) for entry in npc_entries
            ]
            if not schedule:
                schedule = [
                    ScheduleEntry(
                        at_minute=self.rng.randrange(0, 11),
                        location=self.rng.choice(location_ids),
                    )
                ]
            roster.append(
                NpcRosterEntry(
                    id=npc_id,
                    display_name=names[index],
                    start_location=schedule[0].location,
                    schedule=schedule,
                )
            )

            other_ids = [other for other in npc_ids if other != npc_id]
            goals = self.rng.sample(common.GOALS, k=2)
            if npc_id == culprit_id:
                goals = [f"keep the truth about {motive_clause} hidden"[:400], goals[0]]
            identities[npc_id] = Identity(
                id=npc_id,
                name=names[index],
                age=self.rng.randint(22, 65),
                role=common.ROLES[self.rng.randrange(len(common.ROLES))],
                traits=self.rng.sample(common.TRAITS, k=2),
                speech_style=common.SPEECH_STYLES[self.rng.randrange(len(common.SPEECH_STYLES))],
                backstory=common.BACKSTORIES[self.rng.randrange(len(common.BACKSTORIES))].format(
                    town=town
                ),
                goals=goals,
                relationships={
                    other_ids[0]: common.RELATIONSHIPS[
                        self.rng.randrange(len(common.RELATIONSHIPS))
                    ]
                },
                attitude_to_player=common.ATTITUDES[self.rng.randrange(len(common.ATTITUDES))],
            )
        return roster, identities

    # ------------------------------------------------------------------ text helpers

    def _method_clause(self) -> str:
        raw = self.blueprint.crime.method.strip().rstrip(".")
        if " " in raw:
            return raw[:1].lower() + raw[1:]
        return f"carried out the {self.mystery_type.value} using {_human(raw) or 'unknown means'}"

    def _motive_clause(self) -> str:
        raw = self.blueprint.crime.motive.strip().rstrip(".")
        if raw and " " not in raw:
            return _human(raw)
        return raw or "reasons they will not admit"

    def _option_text(self, raw: str, fallback: str) -> str:
        text = raw.strip()
        if " " in text:
            return _sentence(text, fallback)
        human = _human(text)
        return (f"Using {human}." if human else fallback)[:400]

    def _build_accusation_options(
        self,
        correct_method_id: str,
        correct_motive_id: str,
        correct_method_text: str,
        correct_motive_text: str,
    ) -> AccusationOptions:
        methods = [(correct_method_id, correct_method_text)]
        for option_id, text in _METHOD_POOL:
            if len(methods) == 4:
                break
            if option_id != correct_method_id:
                methods.append((option_id, text))
        motives = [(correct_motive_id, correct_motive_text)]
        for option_id, text in _MOTIVE_POOL:
            if len(motives) == 4:
                break
            if option_id != correct_motive_id:
                motives.append((option_id, text))
        return AccusationOptions(
            methods=[MethodOption(id=option_id, text=text) for option_id, text in methods],
            motives=[MotiveOption(id=option_id, text=text) for option_id, text in motives],
        )

    # ------------------------------------------------------------------ compile

    def compile(self) -> Bundle:
        """Execute full compilation into validated Pydantic Bundle."""
        town = common.TOWN_NAMES[self.rng.randrange(len(common.TOWN_NAMES))]
        locations, alias = self._build_locations()
        self._loc_alias = alias
        location_ids = [loc.id for loc in locations]
        location_names = {loc.id: loc.name for loc in locations}
        scene_id = self._resolve_location(self.blueprint.crime.scene, location_ids)
        scene_name = location_names[scene_id]
        alibi_loc = next((loc_id for loc_id in location_ids if loc_id != scene_id), scene_id)
        alibi_name = location_names[alibi_loc]

        crime_minute = max(0, min(10, int(self.blueprint.crime.time)))
        npc_ids = self._build_npc_ids()
        culprit_id = npc_ids[0]
        method_clause = self._method_clause()
        motive_clause = self._motive_clause()
        correct_method_id = f"meth_{_identifier(self.blueprint.crime.method, 'unknown')}"[:64]
        correct_motive_id = f"mot_{_identifier(self.blueprint.crime.motive, 'unknown')}"[:64]

        timeline = self._build_timeline(npc_ids, location_ids, culprit_id, scene_id, crime_minute)
        roster, identities = self._build_roster_and_identities(
            npc_ids, location_ids, town, timeline, culprit_id, motive_clause
        )

        # 1. Memories: the culprit hides the truth, everyone else holds an alibi.
        facts_by_npc: dict[str, list[Fact]] = {npc_id: [] for npc_id in npc_ids}
        did_id = _fact_id(culprit_id, "crime_did")
        motive_id = _fact_id(culprit_id, "motive")
        trace_id = _fact_id(culprit_id, "trace_left")
        claim_id = _fact_id(culprit_id, "alibi_claim")
        cover_id = _fact_id(culprit_id, "cover")
        facts_by_npc[culprit_id].extend(
            [
                Fact(
                    id=did_id,
                    who=culprit_id,
                    what=(f"I {method_clause} at the {scene_name} during minute {crime_minute}."),
                    where=scene_id,
                    when=f"minute {crime_minute}",
                    source=FactSource.DID,
                    secret=True,
                    disclosure=Disclosure.LIE,
                    cover_story_id=cover_id,
                ),
                Fact(
                    id=motive_id,
                    who=culprit_id,
                    what=f"What I did, I did to {motive_clause}.",
                    where=scene_id,
                    when=f"minute {crime_minute}",
                    source=FactSource.DID,
                    secret=True,
                    disclosure=Disclosure.HIDE,
                ),
                Fact(
                    id=trace_id,
                    who=culprit_id,
                    what=self.rng.choice(common.TRACE_LINES).format(place=scene_name),
                    where=scene_id,
                    when=f"minute {crime_minute}",
                    source=FactSource.DID,
                    secret=True,
                    disclosure=Disclosure.HIDE,
                ),
                Fact(
                    id=claim_id,
                    who=culprit_id,
                    what=f"I spent minute {crime_minute} at the {alibi_name}, with witnesses.",
                    where=alibi_loc,
                    when=f"minute {crime_minute}",
                    source=FactSource.HEARD,
                    secret=False,
                    disclosure=Disclosure.IF_ASKED,
                ),
            ]
        )

        knowledge: dict[str, list[str]] = {}
        for raw_npc, claims in self.blueprint.knowledge.items():
            knowledge.setdefault(_identifier(raw_npc, "npc"), []).extend(claims)

        for npc_id in npc_ids:
            if npc_id == culprit_id:
                continue
            entries = [entry for entry in timeline if entry.who == npc_id]
            alibi_where = alibi_loc
            if entries:
                nearest = min(entries, key=lambda entry: (abs(entry.t - crime_minute), entry.t))
                if nearest.where != scene_id:
                    alibi_where = nearest.where
            facts_by_npc[npc_id].extend(
                [
                    Fact(
                        id=_fact_id(npc_id, "alibi"),
                        who=npc_id,
                        what=self.rng.choice(common.ALIBI_LINES).format(
                            place=location_names[alibi_where]
                        ),
                        where=alibi_where,
                        when=f"minute {crime_minute}",
                        source=FactSource.WITNESSED,
                        secret=False,
                        disclosure=Disclosure.VOLUNTEER,
                    ),
                    Fact(
                        id=_fact_id(npc_id, "witness"),
                        who=npc_id,
                        what=self.rng.choice(common.WITNESS_LINES).format(place=scene_name),
                        where=scene_id,
                        when=f"minute {crime_minute}",
                        source=FactSource.HEARD,
                        secret=False,
                        disclosure=Disclosure.IF_ASKED,
                    ),
                ]
            )
        for npc_id, claims in knowledge.items():
            if npc_id not in facts_by_npc:
                continue
            where = next((fact.where for fact in facts_by_npc[npc_id]), location_ids[0])
            for index, claim in enumerate(claims, start=1):
                text = claim.strip()
                if not text or text.lower().startswith("alibi:"):
                    continue
                facts_by_npc[npc_id].append(
                    Fact(
                        id=_fact_id(npc_id, f"knows_{index}"),
                        who=npc_id,
                        what=f"I remember that {_human(text)}."[:4000],
                        where=where,
                        when="that day",
                        source=FactSource.HEARD,
                        secret=False,
                        disclosure=Disclosure.IF_ASKED,
                    )
                )

        def fact_owner(fact_id: str) -> str | None:
            for npc_id, facts in facts_by_npc.items():
                if any(fact.id == fact_id for fact in facts):
                    return npc_id
            return None

        def herring_fact(npc_id: str) -> str:
            fact_id = _fact_id(npc_id, "herring")
            if fact_owner(fact_id) is None:
                facts_by_npc[npc_id].append(
                    Fact(
                        id=fact_id,
                        who=npc_id,
                        what=(f"They secretly {self.rng.choice(common.HERRING_ACTS)}.")[:4000],
                        where=alibi_loc,
                        when="recently",
                        source=FactSource.HEARD,
                        secret=True,
                        disclosure=Disclosure.HIDE,
                    )
                )
            return fact_id

        def resolve_target(raw: str) -> str | None:
            npc_id = _identifier(raw, "npc")
            if npc_id in npc_ids:
                return npc_id
            short = npc_id.removeprefix("npc_")
            return next(
                (candidate for candidate in npc_ids if candidate.removeprefix("npc_") == short),
                None,
            )

        innocent_ids = [npc_id for npc_id in npc_ids if npc_id != culprit_id]

        def implied_fact(target_raw: str, proves: str) -> str:
            target = resolve_target(target_raw)
            lower = proves.strip().lower()
            if lower == "red_herring":
                return herring_fact(target if target and target != culprit_id else innocent_ids[0])
            if lower == "alibi":
                return _fact_id(target or innocent_ids[0], "alibi")
            if target == culprit_id:
                return motive_id if lower in ("mot", "motive", "why") else did_id
            if target is None:
                target = innocent_ids[0]
            if lower in ("mot", "motive", "why"):
                return herring_fact(target)
            return _fact_id(target, "witness")

        def revealer_for(owner_npc: str | None) -> str:
            if owner_npc is not None and owner_npc != culprit_id:
                return owner_npc
            return innocent_ids[0]

        # 2. Clues: compile the blueprint clues first, then guarantee coverage.
        taken_clue_ids: set[str] = set()

        def clue_id(raw: str, fallback: str) -> str:
            candidate = _identifier(raw, fallback)
            stem, index = candidate, 2
            while candidate in taken_clue_ids:
                suffix = f"_{index}"
                candidate = f"{stem[: 64 - len(suffix)]}{suffix}"
                index += 1
            taken_clue_ids.add(candidate)
            return candidate

        compiled: list[Clue] = []
        for index, spec in enumerate(self.blueprint.clues, start=1):
            fact = implied_fact(spec.links, spec.proves)
            owner_npc = fact_owner(fact)
            clue_type = spec.clue_type.strip().lower()
            discovery = (
                DiscoveryMethod.NPC_REVEAL
                if any(hint in clue_type for hint in _REVEAL_TYPES)
                else DiscoveryMethod.EXAMINE
            )
            where = self._resolve_location(spec.location, location_ids)
            revealer = revealer_for(owner_npc) if discovery is DiscoveryMethod.NPC_REVEAL else None
            readable = _human(spec.id) or f"clue {index}"
            if discovery is DiscoveryMethod.NPC_REVEAL:
                description = (
                    f"{identities[revealer].name} recalls a {clue_type or 'curious'} detail: "
                    f"{readable}."
                )
            else:
                description = (
                    f"At the {location_names[where]}, a {clue_type or 'physical'} trace: "
                    f"{readable}."
                )
            compiled.append(
                Clue(
                    id=clue_id(spec.id, f"clue_{index}"),
                    location_id=where,
                    description=description,
                    discovery=discovery,
                    revealed_by_npc=revealer,
                    implies=[fact],
                )
            )

        def implicating(clue: Clue, predicate) -> bool:
            return any(predicate(fact_id) for fact_id in clue.implies)

        def culprit_evidence(clue: Clue) -> bool:
            def is_culprit_did(fact_id: str) -> bool:
                return fact_id in {did_id, motive_id, trace_id}

            return implicating(clue, is_culprit_did)

        def alibi_of(npc_id: str):
            alibi_id = _fact_id(npc_id, "alibi")
            return lambda clue: alibi_id in clue.implies

        final: list[Clue] = []
        culprit_clue = next((clue for clue in compiled if culprit_evidence(clue)), None)
        if culprit_clue is None:
            culprit_clue = Clue(
                id=clue_id("clue_crime_trace", "clue_crime_trace"),
                location_id=scene_id,
                description=(
                    f"A small detail at the {scene_name} shows exactly how the "
                    f"{self.mystery_type.value} was carried out."
                ),
                discovery=DiscoveryMethod.EXAMINE,
                implies=[trace_id],
            )
        final.append(culprit_clue)

        for npc_id in innocent_ids:
            chosen = next((clue for clue in compiled if alibi_of(npc_id)(clue)), None)
            if chosen is None:
                other = next(other for other in innocent_ids if other != npc_id)
                alibi_where = _fact_where(facts_by_npc[npc_id], _fact_id(npc_id, "alibi"))
                chosen = Clue(
                    id=clue_id(f"clue_{npc_id}_alibi", "clue_alibi"),
                    location_id=alibi_where,
                    description=(
                        f"{identities[other].name} saw {identities[npc_id].name} at the "
                        f"{location_names[alibi_where]} at minute {crime_minute}, "
                        f"and a ledger agrees."
                    ),
                    discovery=DiscoveryMethod.NPC_REVEAL,
                    revealed_by_npc=other,
                    implies=[_fact_id(npc_id, "alibi")],
                )
            if chosen not in final:
                final.append(chosen)

        for clue in compiled:
            if len(final) >= 6:
                break
            if clue not in final:
                final.append(clue)

        spots: dict[str, list[str]] = {loc_id: [] for loc_id in location_ids}
        for clue in final:
            spots[clue.location_id].append(clue.id)
        locations = [loc.model_copy(update={"clue_spots": spots[loc.id]}) for loc in locations]

        # 3. Truth: preserve the blueprint's scene, minute, cast, and red herrings.
        red_herrings: list[RedHerring] = []
        seen_herrings: set[str] = set()
        for spec in self.blueprint.clues:
            if spec.proves.strip().lower() != "red_herring":
                continue
            target = resolve_target(spec.links)
            if target is None or target == culprit_id or target in seen_herrings:
                continue
            seen_herrings.add(target)
            red_herrings.append(
                RedHerring(
                    npc=target,
                    secret=f"They secretly {self.rng.choice(common.HERRING_ACTS)}."[:4000],
                )
            )
            if len(red_herrings) == 2:
                break

        victim_label = _human(self.blueprint.cast.victim)
        if self.mystery_type is MysteryType.THEFT or not victim_label:
            target_label = self.content.TARGETS[self.rng.randrange(len(self.content.TARGETS))]
        else:
            target_label = victim_label
        truth = TruthDocument(
            crime=Crime(
                type=self.mystery_type,
                target=target_label,
                time_window=TimeWindow(
                    start=max(0, crime_minute - 1),
                    end=min(10, crime_minute + 1),
                ),
                location_id=scene_id,
            ),
            timeline=timeline,
            solution=Solution(
                correct_culprit_id=culprit_id,
                correct_method_id=correct_method_id,
                correct_motive_id=correct_motive_id,
                how=self.content.how_text(
                    identities[culprit_id].name,
                    method_clause,
                    target_label,
                    scene_name,
                    crime_minute,
                )[:4000],
                why=self.content.why_text(motive_clause)[:4000],
            ),
            red_herrings=red_herrings,
        )

        # 4. World + NPC files.
        intro = self.blueprint.premise.strip() or self.content.INTRO_FMT.format(
            target=target_label, crime_place=scene_name, town=town
        )
        world = WorldDocument(
            scenario_id=f"case_{self.seed}",
            mystery_type=self.mystery_type,
            tone=self.tone,
            difficulty=self.difficulty,
            title=self.content.TITLE_FMT.format(target=target_label, crime_place=scene_name),
            intro_text=intro[:4000],
            town_name=town,
            locations=locations,
            npcs=roster,
            accusation_options=self._build_accusation_options(
                correct_method_id,
                correct_motive_id,
                self._option_text(self.blueprint.crime.method, "An unknown method."),
                self._option_text(self.blueprint.crime.motive, "An unknown motive."),
            ),
        )

        npc_memories: dict[str, Memory] = {}
        for npc_id in npc_ids:
            cover_story = None
            if npc_id == culprit_id:
                cover_story = CoverStory(
                    id=cover_id,
                    claim=(
                        f"I was at the {alibi_name} all along; I never went near the {scene_name}."
                    )[:4000],
                    supporting_facts=[claim_id],
                )
            npc_memories[npc_id] = Memory(
                npc_id=npc_id,
                facts=facts_by_npc[npc_id],
                cover_story=cover_story,
            )

        bundle = Bundle(
            world=world,
            truth=truth,
            clues=CluesDocument(clues=final),
            npcs={
                npc_id: NpcFiles(identity=identities[npc_id], memory=npc_memories[npc_id])
                for npc_id in npc_ids
            },
        )

        issues = validate_bundle(bundle)
        if issues:
            raise ValueError(f"Compiled bundle failed validation: {[i.message for i in issues]}")

        return bundle

    def verify_solvability(self, bundle: Bundle) -> bool:
        """Prove the culprit is the only NPC the evidence does not clear.

        Every innocent needs a clue-backed alibi, and exactly the culprit may
        own a clue-reachable secret 'did' fact.
        """
        culprit_id = bundle.truth.solution.correct_culprit_id
        facts = {
            fact.id: (npc_id, fact)
            for npc_id, files in bundle.npcs.items()
            for fact in files.memory.facts
        }
        implicated = {
            fact_id for clue in bundle.clues.clues for fact_id in clue.implies if fact_id in facts
        }
        did_owners = {
            facts[fact_id][0]
            for fact_id in implicated
            if facts[fact_id][1].source is FactSource.DID and facts[fact_id][1].secret
        }
        if did_owners != {culprit_id}:
            return False
        for npc_id in bundle.npcs:
            if npc_id == culprit_id:
                continue
            if _fact_id(npc_id, "alibi") not in implicated:
                return False
        return True


def _fact_where(facts: list[Fact], fact_id: str) -> str:
    return next(fact.where for fact in facts if fact.id == fact_id)
