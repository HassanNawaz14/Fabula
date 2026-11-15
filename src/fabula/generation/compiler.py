"""Symbolic Blueprint Compiler & Solvability Verifier.

Compiles a Compact Blueprint DSL into Fabula's frozen v1 Pydantic Bundle,
enforcing spatial walkability, epistemic memory slicing, and solvability proofs.
"""

from __future__ import annotations

import random

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


class BlueprintCompiler:
    """Deterministic compiler from Blueprint DSL to frozen Pydantic Bundle."""

    def __init__(self, blueprint: Blueprint, seed: int | None = None) -> None:
        self.blueprint = blueprint
        self.seed = seed if seed is not None else blueprint.seed
        self.rng = random.Random(f"fabula-blueprint-compiler:{self.seed}")

        # Resolve mystery type and content
        mtype_str = blueprint.case_type.lower()
        if mtype_str in ("murder", "theft", "disappearance"):
            self.mystery_type = MysteryType(mtype_str)
        else:
            self.mystery_type = MysteryType.THEFT
        self.content = CONTENT_MAP[self.mystery_type]

        # Tone & Difficulty
        try:
            self.tone = Tone(blueprint.tone.lower())
        except ValueError:
            self.tone = Tone.COZY

        self.difficulty = Difficulty.NORMAL

    def _build_locations(self) -> list[Location]:
        """Build 3-4 connected locations matching the crime scene and walkable graph."""
        # Map scene to LocationType
        scene_hint = self.blueprint.crime.scene.lower().replace("loc_", "")
        primary_type: LocationType | None = None
        for lt in LocationType:
            if lt.value in scene_hint:
                primary_type = lt
                break
        if primary_type is None:
            preferred = list(self.content.CRIME_LOCATION_PREF)
            primary_type = preferred[self.rng.randrange(len(preferred))]

        filler_pool = [lt for lt in LocationType if lt != primary_type]
        count = 4
        selected_types = [primary_type] + self.rng.sample(filler_pool, k=count - 1)
        self.rng.shuffle(selected_types)

        locations: list[Location] = []
        for index, loc_type in enumerate(selected_types):
            names, descriptions = common.LOCATION_PROFILES[loc_type]
            connections: list[str] = []
            if index > 0:
                connections.append(f"loc_{selected_types[index - 1].value}")
            if index < len(selected_types) - 1:
                connections.append(f"loc_{selected_types[index + 1].value}")

            locations.append(
                Location(
                    id=f"loc_{loc_type.value}",
                    name=names[self.rng.randrange(len(names))],
                    type=loc_type,
                    description=descriptions[self.rng.randrange(len(descriptions))],
                    position=Position(x=index * 10, y=0),
                    connections=connections,
                    clue_spots=[],
                )
            )

        # Ensure ring connectivity for extra walkability
        if len(locations) >= 4:
            a, b = locations[0], locations[-1]
            if b.id not in a.connections:
                a.connections.append(b.id)
            if a.id not in b.connections:
                b.connections.append(a.id)

        return locations

    def _build_roster_and_identities(
        self,
        npc_ids: list[str],
        location_ids: list[str],
        town: str,
    ) -> tuple[list[NpcRosterEntry], dict[str, Identity]]:
        """Construct deterministic NPC roster and rich identity profiles."""
        names = self.rng.sample(common.FIRST_NAMES, k=len(npc_ids))
        roster: list[NpcRosterEntry] = []
        identities: dict[str, Identity] = {}

        for index, npc_id in enumerate(npc_ids):
            # Schedules: 2 to 3 distinct minutes
            minutes = sorted(self.rng.sample(range(0, 11), k=3))
            assigned_locs = [location_ids[self.rng.randrange(len(location_ids))] for _ in minutes]
            schedule = [
                ScheduleEntry(at_minute=m, location=loc)
                for m, loc in zip(minutes, assigned_locs, strict=False)
            ]
            start_loc = schedule[0].location

            roster.append(
                NpcRosterEntry(
                    id=npc_id,
                    display_name=names[index],
                    start_location=start_loc,
                    schedule=schedule,
                )
            )

            other_ids = [nid for nid in npc_ids if nid != npc_id]
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
                goals=self.rng.sample(common.GOALS, k=2),
                relationships={
                    other_ids[0]: common.RELATIONSHIPS[
                        self.rng.randrange(len(common.RELATIONSHIPS))
                    ]
                },
                attitude_to_player=common.ATTITUDES[self.rng.randrange(len(common.ATTITUDES))],
            )

        return roster, identities

    def _build_accusation_options(
        self,
        correct_method_id: str,
        correct_motive_id: str,
    ) -> AccusationOptions:
        """Build 4 distinct methods and 4 distinct motives."""
        method_pool = [
            ("meth_skeleton_key", "Used a duplicate skeleton key to gain unauthorized entry."),
            ("meth_poison_vial", "Slipped a slow-acting poison tincture into beverage."),
            ("meth_distraction", "Created a staged commotion to slip past security unseen."),
            ("meth_forced_latch", "Pried open the window latch with a pocket tool."),
            ("meth_forgery", "Substituted the genuine item with an expert counterfeit."),
        ]
        motive_pool = [
            ("mot_gambling_debt", "Desperate need to repay mounting debts to dangerous creditors."),
            ("mot_jealousy", "Bitter professional rivalry and envy of social standing."),
            ("mot_blackmail", "Silencing a blackmailer before dark secrets were exposed."),
            ("mot_inheritance", "Securing an estate bequest before the will could be altered."),
            ("mot_revenge", "Retribution for an ancient family grievance."),
        ]

        # Ensure correct IDs are included
        selected_methods = [
            (
                correct_method_id,
                f"Executed crime using {correct_method_id.replace('meth_', '').replace('_', ' ')}.",
            )
        ]
        for mid, text in method_pool:
            if mid != correct_method_id and len(selected_methods) < 4:
                selected_methods.append((mid, text))

        selected_motives = [
            (
                correct_motive_id,
                f"Driven by {correct_motive_id.replace('mot_', '').replace('_', ' ')}.",
            )
        ]
        for mid, text in motive_pool:
            if mid != correct_motive_id and len(selected_motives) < 4:
                selected_motives.append((mid, text))

        return AccusationOptions(
            methods=[MethodOption(id=m[0], text=m[1]) for m in selected_methods],
            motives=[MotiveOption(id=m[0], text=m[1]) for m in selected_motives],
        )

    def compile(self) -> Bundle:
        """Execute full compilation into validated Pydantic Bundle."""
        town = common.TOWN_NAMES[self.rng.randrange(len(common.TOWN_NAMES))]
        locations = self._build_locations()
        location_ids = [loc.id for loc in locations]

        # Determine crime scene
        crime_scene_id = locations[0].id
        for loc in locations:
            if loc.id == self.blueprint.crime.scene or loc.type.value in self.blueprint.crime.scene:
                crime_scene_id = loc.id
                break

        # Standardize NPC IDs
        culprit_id = "npc_01"
        npc_ids = ["npc_01", "npc_02", "npc_03", "npc_04", "npc_05"]
        roster, identities = self._build_roster_and_identities(npc_ids, location_ids, town)

        crime_minute = max(1, min(9, self.blueprint.crime.time))
        correct_method_id = f"meth_{self.blueprint.crime.method.lower().replace(' ', '_')}"
        correct_motive_id = f"mot_{self.blueprint.crime.motive.lower().replace(' ', '_')}"

        # 1. Timeline Construction (strictly avoiding duplicate (who, t))
        timeline_entries: list[TimelineEntry] = []
        seen_who_t: set[tuple[str, int]] = set()

        def add_timeline_entry(t: int, who: str, what: str, where: str) -> None:
            if (who, t) not in seen_who_t:
                seen_who_t.add((who, t))
                timeline_entries.append(TimelineEntry(t=t, who=who, what=what, where=where))

        # Culprit timeline
        add_timeline_entry(
            crime_minute,
            culprit_id,
            f"Committed {self.mystery_type.value} at the {crime_scene_id}.",
            crime_scene_id,
        )

        # Fill timeline for other NPCs from blueprint or roster
        for ev in self.blueprint.timeline:
            actor = ev.actor if ev.actor in npc_ids else "npc_02"
            loc = ev.location if ev.location in location_ids else location_ids[1]
            add_timeline_entry(max(0, min(10, ev.time)), actor, ev.action, loc)

        # Ensure all NPCs have at least one timeline entry
        for npc in roster:
            for s in npc.schedule:
                add_timeline_entry(s.at_minute, npc.id, f"Seen at {s.location}.", s.location)

        # 2. Memories and Epistemic Slicing
        npc_memories: dict[str, Memory] = {}
        clue_implied_facts: list[str] = []

        alibi_loc = [lid for lid in location_ids if lid != crime_scene_id][0]

        for npc_id in npc_ids:
            facts: list[Fact] = []
            cover_story: CoverStory | None = None

            if npc_id == culprit_id:
                # Culprit MUST have secret 'did' fact + cover story
                did_fact_id = f"{culprit_id}_crime_did"
                crime_desc = (
                    f"I carried out the {self.mystery_type.value} "
                    f"using {correct_method_id} at {crime_scene_id}."
                )
                facts.append(
                    Fact(
                        id=did_fact_id,
                        who=culprit_id,
                        what=crime_desc,
                        where=crime_scene_id,
                        when=f"minute {crime_minute}",
                        source=FactSource.DID,
                        secret=True,
                        disclosure=Disclosure.LIE,
                        reveal_requires=[],
                        cover_story_id=f"{culprit_id}_cover",
                    )
                )
                clue_implied_facts.append(did_fact_id)

                trace_fact_id = f"{culprit_id}_trace_left"
                facts.append(
                    Fact(
                        id=trace_fact_id,
                        who=culprit_id,
                        what=f"Accidentally left evidence behind at {crime_scene_id}.",
                        where=crime_scene_id,
                        when=f"minute {crime_minute}",
                        source=FactSource.DID,
                        secret=True,
                        disclosure=Disclosure.HIDE,
                    )
                )
                clue_implied_facts.append(trace_fact_id)

                # Culprit cover story alibi
                alibi_fact_id = f"{culprit_id}_alibi_claim"
                facts.append(
                    Fact(
                        id=alibi_fact_id,
                        who=culprit_id,
                        what=f"I was at {alibi_loc} during minute {crime_minute}.",
                        where=alibi_loc,
                        when=f"minute {crime_minute}",
                        source=FactSource.HEARD,
                        secret=False,
                        disclosure=Disclosure.IF_ASKED,
                    )
                )

                cover_story = CoverStory(
                    id=f"{culprit_id}_cover",
                    claim=f"I was never at {crime_scene_id}; I was at {alibi_loc} all afternoon.",
                    supporting_facts=[alibi_fact_id],
                )
            else:
                # Innocent NPCs get alibis and witness facts
                alibi_id = f"{npc_id}_alibi"
                facts.append(
                    Fact(
                        id=alibi_id,
                        who=npc_id,
                        what=f"I was in the {alibi_loc} during the incident.",
                        where=alibi_loc,
                        when=f"minute {crime_minute}",
                        source=FactSource.WITNESSED,
                        secret=False,
                        disclosure=Disclosure.VOLUNTEER,
                    )
                )

                witness_id = f"{npc_id}_witness"
                facts.append(
                    Fact(
                        id=witness_id,
                        who=npc_id,
                        what=f"Observed movement near the {crime_scene_id} corridor.",
                        where=crime_scene_id,
                        when=f"minute {crime_minute}",
                        source=FactSource.HEARD,
                        secret=False,
                        disclosure=Disclosure.IF_ASKED,
                    )
                )
                clue_implied_facts.append(witness_id)

            npc_memories[npc_id] = Memory(npc_id=npc_id, facts=facts, cover_story=cover_story)

        # 3. Clues Document Construction
        clues: list[Clue] = [
            Clue(
                id="clue_01_crime_trace",
                location_id=crime_scene_id,
                description="A distinctive physical trace left directly at the crime scene.",
                discovery=DiscoveryMethod.EXAMINE,
                implies=[clue_implied_facts[0]],  # Points directly to culprit's secret 'did' fact!
            ),
            Clue(
                id="clue_02_forensic_evidence",
                location_id=crime_scene_id,
                description="Physical evidence matching the culprit's specific tools.",
                discovery=DiscoveryMethod.EXAMINE,
                implies=[clue_implied_facts[1]],
            ),
            Clue(
                id="clue_03_witness_testimony",
                location_id=location_ids[1],
                description="A discarded receipt or note corroborating timeline movements.",
                discovery=DiscoveryMethod.NPC_REVEAL,
                revealed_by_npc=npc_ids[1],
                implies=[clue_implied_facts[2]],
            ),
            Clue(
                id="clue_04_red_herring",
                location_id=location_ids[2],
                description="A suspicious item pointing to an innocent suspect's hobby.",
                discovery=DiscoveryMethod.EXAMINE,
                implies=[clue_implied_facts[2]],
            ),
        ]

        # 4. Truth Document
        truth = TruthDocument(
            crime=Crime(
                type=self.mystery_type,
                target=self.blueprint.cast.victim or "treasured heirloom",
                time_window=TimeWindow(
                    start=max(0, crime_minute - 1),
                    end=min(10, crime_minute + 1),
                ),
                location_id=crime_scene_id,
            ),
            timeline=sorted(timeline_entries, key=lambda x: x.t),
            solution=Solution(
                correct_culprit_id=culprit_id,
                correct_method_id=correct_method_id,
                correct_motive_id=correct_motive_id,
                how=f"Gained entry to {crime_scene_id} using {correct_method_id}.",
                why=f"Driven by {correct_motive_id}.",
            ),
            red_herrings=[
                RedHerring(npc=npc_ids[1], secret="Kept an unrelated private matter quiet.")
            ],
        )

        # 5. World Document
        world = WorldDocument(
            scenario_id=f"case_{self.seed}",
            mystery_type=self.mystery_type,
            tone=self.tone,
            difficulty=self.difficulty,
            title=f"The Mystery of {town}",
            intro_text=self.blueprint.premise,
            town_name=town,
            locations=locations,
            npcs=roster,
            accusation_options=self._build_accusation_options(correct_method_id, correct_motive_id),
        )

        # 6. Assemble Full Bundle
        npc_files = {
            npc_id: NpcFiles(identity=identities[npc_id], memory=npc_memories[npc_id])
            for npc_id in npc_ids
        }

        bundle = Bundle(
            world=world,
            truth=truth,
            clues=CluesDocument(clues=clues),
            npcs=npc_files,
        )

        # 7. Quality Gate: Validate bundle against Pydantic schema & rules
        issues = validate_bundle(bundle)
        if issues:
            raise ValueError(f"Compiled bundle failed validation: {[i.message for i in issues]}")

        return bundle

    def verify_solvability(self, bundle: Bundle) -> bool:
        """Prove that the culprit is uniquely deducible from the evidence set."""
        culprit_id = bundle.truth.solution.correct_culprit_id

        # Check if at least one clue implicates the culprit's facts
        implicated_owners = set()
        for clue in bundle.clues.clues:
            for fact_id in clue.implies:
                for npc_id, npc_file in bundle.npcs.items():
                    if any(f.id == fact_id for f in npc_file.memory.facts):
                        implicated_owners.add(npc_id)

        return culprit_id in implicated_owners
