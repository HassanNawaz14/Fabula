from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from fabula.schemas.bundle import Bundle
from fabula.schemas.enums import Disclosure, FactSource


class IssueCode(StrEnum):
    E_DISCONNECTED_GRAPH = "E_DISCONNECTED_GRAPH"
    E_SCHEDULE_CONFLICT = "E_SCHEDULE_CONFLICT"
    E_TIMELINE_CONFLICT = "E_TIMELINE_CONFLICT"
    E_BAD_TIME_WINDOW = "E_BAD_TIME_WINDOW"
    E_CULPRIT_MISSING_ACCOUNT = "E_CULPRIT_MISSING_ACCOUNT"
    E_LIE_WITHOUT_COVER = "E_LIE_WITHOUT_COVER"
    E_CLUE_IMPLIES_UNKNOWN = "E_CLUE_IMPLIES_UNKNOWN"
    E_NO_CULPRIT_EVIDENCE = "E_NO_CULPRIT_EVIDENCE"


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: IssueCode
    message: str
    where: str


def _check_graph(bundle: Bundle) -> list[Issue]:
    locations = [loc.id for loc in bundle.world.locations]
    adjacency: dict[str, set[str]] = {loc_id: set() for loc_id in locations}
    for loc in bundle.world.locations:
        for neighbor in loc.connections:
            if neighbor in adjacency:
                adjacency[loc.id].add(neighbor)
                adjacency[neighbor].add(loc.id)
    start = locations[0]
    visited = {start}
    frontier = [start]
    while frontier:
        current = frontier.pop()
        for neighbor in adjacency[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                frontier.append(neighbor)
    missing = sorted(set(locations) - visited)
    if missing:
        return [
            Issue(
                code=IssueCode.E_DISCONNECTED_GRAPH,
                message=f"locations are not fully walkable: unreachable {missing}",
                where="world.locations",
            )
        ]
    return []


def _check_schedules(bundle: Bundle) -> list[Issue]:
    issues = []
    for npc in bundle.world.npcs:
        minutes = [entry.at_minute for entry in npc.schedule]
        if len(minutes) != len(set(minutes)):
            issues.append(
                Issue(
                    code=IssueCode.E_SCHEDULE_CONFLICT,
                    message=f"npc {npc.id} has two waypoints at the same minute",
                    where=f"world.npcs[{npc.id}].schedule",
                )
            )
    return issues


def _check_timeline(bundle: Bundle) -> list[Issue]:
    issues = []
    seen: set[tuple[str, int]] = set()
    for index, entry in enumerate(bundle.truth.timeline):
        key = (entry.who, entry.t)
        if key in seen:
            issues.append(
                Issue(
                    code=IssueCode.E_TIMELINE_CONFLICT,
                    message=f"{entry.who} is placed in two places at minute {entry.t}",
                    where=f"truth.timeline[{index}]",
                )
            )
        seen.add(key)
    return issues


def _check_time_window(bundle: Bundle) -> list[Issue]:
    window = bundle.truth.crime.time_window
    if window.start > window.end:
        return [
            Issue(
                code=IssueCode.E_BAD_TIME_WINDOW,
                message=f"crime window starts at {window.start} but ends at {window.end}",
                where="truth.crime.time_window",
            )
        ]
    return []


def _fact_index(bundle: Bundle) -> dict[str, tuple[str, object]]:
    index: dict[str, tuple[str, object]] = {}
    for npc_id, files in bundle.npcs.items():
        for fact in files.memory.facts:
            index[fact.id] = (npc_id, fact)
    return index


def _check_culprit_account(bundle: Bundle) -> list[Issue]:
    culprit_id = bundle.truth.solution.correct_culprit_id
    memory = bundle.npcs[culprit_id].memory
    has_account = any(fact.source == FactSource.DID and fact.secret for fact in memory.facts)
    if not has_account:
        return [
            Issue(
                code=IssueCode.E_CULPRIT_MISSING_ACCOUNT,
                message=f"culprit {culprit_id} has no secret 'did' fact about the crime",
                where=f"npcs[{culprit_id}]/memory.json",
            )
        ]
    return []


def _check_lies_have_cover(bundle: Bundle) -> list[Issue]:
    issues = []
    for npc_id, files in bundle.npcs.items():
        for fact in files.memory.facts:
            if fact.disclosure == Disclosure.LIE and files.memory.cover_story is None:
                issues.append(
                    Issue(
                        code=IssueCode.E_LIE_WITHOUT_COVER,
                        message=f"fact {fact.id} of {npc_id} may lie but has no cover story",
                        where=f"npcs[{npc_id}]/memory.json",
                    )
                )
    return issues


def _check_clue_references(bundle: Bundle) -> list[Issue]:
    facts = _fact_index(bundle)
    issues = []
    for clue in bundle.clues.clues:
        for ref in clue.implies:
            if ref not in facts:
                issues.append(
                    Issue(
                        code=IssueCode.E_CLUE_IMPLIES_UNKNOWN,
                        message=f"clue {clue.id} implies unknown fact {ref}",
                        where=f"clues[{clue.id}]",
                    )
                )
    return issues


def _check_culprit_evidence(bundle: Bundle) -> list[Issue]:
    facts = _fact_index(bundle)
    culprit_id = bundle.truth.solution.correct_culprit_id
    for clue in bundle.clues.clues:
        for ref in clue.implies:
            owner, fact = facts.get(ref, (None, None))
            if owner == culprit_id and fact is not None:
                return []
    return [
        Issue(
            code=IssueCode.E_NO_CULPRIT_EVIDENCE,
            message="no clue points at any fact owned by the culprit; the case is unsolvable",
            where="clues",
        )
    ]


def validate_bundle(bundle: Bundle) -> list[Issue]:
    issues: list[Issue] = []
    issues += _check_graph(bundle)
    issues += _check_schedules(bundle)
    issues += _check_timeline(bundle)
    issues += _check_time_window(bundle)
    issues += _check_culprit_account(bundle)
    issues += _check_lies_have_cover(bundle)
    issues += _check_clue_references(bundle)
    issues += _check_culprit_evidence(bundle)
    return issues


def is_valid(bundle: Bundle) -> bool:
    return not validate_bundle(bundle)
