import copy

from fabula.schemas import Bundle, IssueCode, validate_bundle
from test_schemas import build_bundle_raw


def make_bundle(**mutate) -> Bundle:
    raw = build_bundle_raw()
    mutate(raw)
    return Bundle.model_validate(raw)


def codes(raw_mutator) -> set[IssueCode]:
    raw = build_bundle_raw()
    raw_mutator(raw)
    bundle = Bundle.model_validate(raw)
    return {issue.code for issue in validate_bundle(bundle)}


def test_valid_bundle_has_no_issues() -> None:
    bundle = Bundle.model_validate(build_bundle_raw())
    assert validate_bundle(bundle) == []


def test_detects_disconnected_graph() -> None:
    def mutate(raw: dict) -> None:
        locations = build_bundle_raw(npc_count=5, location_count=4, clue_count=4)["world"][
            "locations"
        ]
        raw["world"]["locations"] = locations
        for location in raw["world"]["locations"]:
            if location["id"] in {"market", "library"}:
                location["connections"] = [
                    ref for ref in location["connections"] if ref in {"market", "library"}
                ]
            else:
                location["connections"] = [
                    ref for ref in location["connections"] if ref in {"parking", "park"}
                ]

    assert IssueCode.E_DISCONNECTED_GRAPH in codes(mutate)


def test_detects_schedule_conflict() -> None:
    def mutate(raw: dict) -> None:
        schedule = raw["world"]["npcs"][0]["schedule"]
        schedule.append(
            {
                "at_minute": schedule[0]["at_minute"],
                "location": raw["world"]["locations"][1]["id"],
            }
        )

    assert IssueCode.E_SCHEDULE_CONFLICT in codes(mutate)


def test_detects_timeline_conflict() -> None:
    def mutate(raw: dict) -> None:
        entry = copy.deepcopy(raw["truth"]["timeline"][0])
        entry["where"] = raw["world"]["locations"][-1]["id"]
        raw["truth"]["timeline"].append(entry)

    assert IssueCode.E_TIMELINE_CONFLICT in codes(mutate)


def test_detects_bad_time_window() -> None:
    def mutate(raw: dict) -> None:
        raw["truth"]["crime"]["time_window"] = {"start": 6, "end": 2}

    assert IssueCode.E_BAD_TIME_WINDOW in codes(mutate)


def test_detects_culprit_without_account() -> None:
    def mutate(raw: dict) -> None:
        for fact in raw["npcs"]["npc_03"]["memory"]["facts"]:
            fact["secret"] = False

    assert IssueCode.E_CULPRIT_MISSING_ACCOUNT in codes(mutate)


def test_detects_lie_without_cover_story() -> None:
    def mutate(raw: dict) -> None:
        raw["npcs"]["npc_01"]["memory"]["facts"][0]["disclosure"] = "lie"

    assert IssueCode.E_LIE_WITHOUT_COVER in codes(mutate)


def test_detects_clue_implying_unknown_fact() -> None:
    def mutate(raw: dict) -> None:
        raw["clues"]["clues"][0]["implies"] = ["f_missing"]

    assert IssueCode.E_CLUE_IMPLIES_UNKNOWN in codes(mutate)


def test_detects_case_without_culprit_evidence() -> None:
    def mutate(raw: dict) -> None:
        other_fact = raw["npcs"]["npc_01"]["memory"]["facts"][0]["id"]
        for clue in raw["clues"]["clues"]:
            clue["implies"] = [other_fact]

    assert IssueCode.E_NO_CULPRIT_EVIDENCE in codes(mutate)


def test_issue_messages_are_specific() -> None:
    raw = build_bundle_raw()
    raw["truth"]["crime"]["time_window"] = {"start": 9, "end": 1}
    issues = validate_bundle(Bundle.model_validate(raw))
    window_issues = [issue for issue in issues if issue.code == IssueCode.E_BAD_TIME_WINDOW]
    assert len(window_issues) == 1
    assert "truth.crime.time_window" in window_issues[0].where
