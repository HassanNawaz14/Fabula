"""Compact Causal Blueprint DSL for Fabula Neurosymbolic Generation.

Encodes high-level narrative intent into a token-dense causal manifest (~140-160 tokens)
eliminating the 65% token syntax tax of raw JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TimelineEvent:
    time: int
    actor: str
    location: str
    action: str


@dataclass(slots=True)
class ClueSpec:
    id: str
    location: str
    clue_type: str
    links: str
    proves: str


@dataclass(slots=True)
class CastSpec:
    victim: str
    culprit: str
    suspects: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CrimeSpec:
    motive: str
    method: str
    scene: str
    time: int


@dataclass(slots=True)
class Blueprint:
    case_type: str
    tone: str
    seed: int
    premise: str
    cast: CastSpec
    crime: CrimeSpec
    timeline: list[TimelineEvent] = field(default_factory=list)
    clues: list[ClueSpec] = field(default_factory=list)
    knowledge: dict[str, list[str]] = field(default_factory=dict)


def parse_dsl(text: str) -> Blueprint:
    """Parse a Compact Blueprint DSL string into a structured Blueprint object."""
    case_type = "theft"
    tone = "cozy"
    seed = 42
    premise = "A mysterious occurrence requires investigation."
    victim = "victim"
    culprit = "npc_01"
    suspects: list[str] = []
    motive = "debt"
    method = "theft"
    scene = "loc_library"
    crime_time = 5

    timeline: list[TimelineEvent] = []
    clues: list[ClueSpec] = []
    knowledge: dict[str, list[str]] = {}

    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]

    for line in lines:
        if line.startswith("[CASE:") and line.endswith("]"):
            # [CASE:theft|cozy|seed_101]
            inner = line[6:-1]
            parts = inner.split("|")
            if len(parts) >= 1 and parts[0]:
                case_type = parts[0].strip().lower()
            if len(parts) >= 2 and parts[1]:
                tone = parts[1].strip().lower()
            if len(parts) >= 3 and parts[2]:
                seed_str = parts[2].strip().replace("seed_", "").replace("seed:", "")
                try:
                    seed = int(seed_str)
                except ValueError:
                    seed = 42

        elif line.startswith("PREMISE:"):
            premise = line[8:].strip()

        elif line.startswith("CAST:"):
            # vict:lady_eleanor | culp:npc_butler | susp:npc_maid,npc_gardener
            parts = [p.strip() for p in line[5:].split("|")]
            for part in parts:
                if ":" in part:
                    k, v = part.split(":", 1)
                    k, v = k.strip().lower(), v.strip()
                    if k in ("vict", "victim"):
                        victim = v
                    elif k in ("culp", "culprit"):
                        culprit = v
                    elif k in ("susp", "suspects"):
                        suspects = [s.strip() for s in v.split(",") if s.strip()]

        elif line.startswith("CRIME:"):
            # mot:gambling_debt | meth:skeleton_key | scene:loc_library | time:5
            parts = [p.strip() for p in line[6:].split("|")]
            for part in parts:
                if ":" in part:
                    k, v = part.split(":", 1)
                    k, v = k.strip().lower(), v.strip()
                    if k in ("mot", "motive"):
                        motive = v
                    elif k in ("meth", "method"):
                        method = v
                    elif k in ("scene", "loc", "location"):
                        scene = v
                    elif k in ("time", "minute"):
                        try:
                            crime_time = int(v)
                        except ValueError:
                            crime_time = 5

        elif line.startswith("- ") and " | " in line:
            parts = [p.strip() for p in line[2:].split("|")]
            # Check timeline: time | actor | loc | action
            if len(parts) >= 4 and parts[0].isdigit():
                t = int(parts[0])
                actor = parts[1]
                loc = parts[2]
                action = parts[3]
                timeline.append(TimelineEvent(time=t, actor=actor, location=loc, action=action))

            # Check clue: id | loc | type | links:target | proves:fact
            # Or red herring: id | loc | type | red_herring:target
            elif len(parts) >= 4 and any(
                p.startswith("links:") or p.startswith("red_herring:") for p in parts
            ):
                clue_id = parts[0]
                loc = parts[1]
                ctype = parts[2]
                links = ""
                proves = ""
                for p in parts[3:]:
                    if p.startswith("links:"):
                        links = p[6:].strip()
                    elif p.startswith("proves:"):
                        proves = p[7:].strip()
                    elif p.startswith("red_herring:"):
                        links = p[12:].strip()
                        proves = "red_herring"
                clues.append(
                    ClueSpec(id=clue_id, location=loc, clue_type=ctype, links=links, proves=proves)
                )

            # Check knowledge: npc_id | claim1 | claim2
            elif len(parts) >= 2 and ":" in parts[1]:
                npc_id = parts[0]
                claims = parts[1:]
                knowledge.setdefault(npc_id, []).extend(claims)

    cast = CastSpec(victim=victim, culprit=culprit, suspects=suspects)
    crime = CrimeSpec(motive=motive, method=method, scene=scene, time=crime_time)

    return Blueprint(
        case_type=case_type,
        tone=tone,
        seed=seed,
        premise=premise,
        cast=cast,
        crime=crime,
        timeline=timeline,
        clues=clues,
        knowledge=knowledge,
    )


def format_dsl(blueprint: Blueprint) -> str:
    """Format a Blueprint object back into standard Compact Blueprint DSL text."""
    suspects_str = ",".join(blueprint.cast.suspects)
    crime_str = (
        f"CRIME: mot:{blueprint.crime.motive} | meth:{blueprint.crime.method} "
        f"| scene:{blueprint.crime.scene} | time:{blueprint.crime.time}"
    )
    lines = [
        f"[CASE:{blueprint.case_type}|{blueprint.tone}|seed_{blueprint.seed}]",
        f"PREMISE: {blueprint.premise}",
        f"CAST: vict:{blueprint.cast.victim} | culp:{blueprint.cast.culprit} | susp:{suspects_str}",
        crime_str,
        "TIMELINE:",
    ]
    for ev in blueprint.timeline:
        lines.append(f"- {ev.time} | {ev.actor} | {ev.location} | {ev.action}")

    lines.append("CLUES:")
    for c in blueprint.clues:
        if c.proves == "red_herring":
            lines.append(f"- {c.id} | {c.location} | {c.clue_type} | red_herring:{c.links}")
        else:
            lines.append(
                f"- {c.id} | {c.location} | {c.clue_type} | links:{c.links} | proves:{c.proves}"
            )

    lines.append("KNOWLEDGE:")
    for npc_id, claims in blueprint.knowledge.items():
        claims_str = " | ".join(claims)
        lines.append(f"- {npc_id} | {claims_str}")

    return "\n".join(lines)
