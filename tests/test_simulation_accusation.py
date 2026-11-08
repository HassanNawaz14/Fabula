from __future__ import annotations

import dataclasses
import json

import pytest

from fabula.simulation import AccusationService, FakeClock


def make_service(loaded, clock=None) -> AccusationService:
    return AccusationService(loaded.accusation_truth(), loaded.world, clock=clock)


def wrong_ids(loaded):
    truth = loaded.accusation_truth()
    solution = truth.solution
    wrong_who = next(
        roster_entry.id
        for roster_entry in loaded.world.npcs
        if roster_entry.id != solution.correct_culprit_id
    )
    wrong_how = next(
        option.id
        for option in loaded.world.accusation_options.methods
        if option.id != solution.correct_method_id
    )
    wrong_why = next(
        option.id
        for option in loaded.world.accusation_options.motives
        if option.id != solution.correct_motive_id
    )
    return wrong_who, wrong_how, wrong_why


def test_correct_accusation_wins_immediately(loaded) -> None:
    solution = loaded.accusation_truth().solution
    service = make_service(loaded)

    result = service.submit(
        solution.correct_culprit_id,
        solution.correct_method_id,
        solution.correct_motive_id,
    )

    assert result.correct is True
    assert result.terminal is True
    assert result.timed_out is False
    assert result.attempts_remaining == 2
    assert service.attempts_used == 1
    with pytest.raises(RuntimeError):
        service.submit(
            solution.correct_culprit_id,
            solution.correct_method_id,
            solution.correct_motive_id,
        )


def test_wrong_attempt_exposes_no_per_component_feedback(loaded) -> None:
    solution = loaded.accusation_truth().solution
    wrong_who, _, _ = wrong_ids(loaded)
    service = make_service(loaded)

    result = service.submit(
        wrong_who,
        solution.correct_method_id,
        solution.correct_motive_id,
    )

    assert result.correct is False
    assert result.terminal is False
    assert result.attempts_remaining == 2
    public_fields = {field.name for field in dataclasses.fields(result)}
    assert "who_correct" not in public_fields
    assert "how_correct" not in public_fields
    assert "why_correct" not in public_fields

    record = service.attempt_log()[0]
    assert record.who_correct is False
    assert record.how_correct is True
    assert record.why_correct is True


def test_three_wrong_attempts_end_the_game(loaded) -> None:
    wrong_who, wrong_how, wrong_why = wrong_ids(loaded)
    service = make_service(loaded)

    results = [service.submit(wrong_who, wrong_how, wrong_why) for _ in range(3)]

    assert [result.attempts_remaining for result in results] == [2, 1, 0]
    assert [result.terminal for result in results] == [False, False, True]
    assert service.attempts_used == 3
    with pytest.raises(RuntimeError):
        service.submit(wrong_who, wrong_how, wrong_why)


def test_timeout_ends_the_game_without_truth_leakage(loaded) -> None:
    service = make_service(loaded)

    result = service.timeout()

    assert result.correct is False
    assert result.terminal is True
    assert result.timed_out is True
    assert result.attempts_remaining == 3
    with pytest.raises(RuntimeError):
        service.timeout()


def test_unknown_ids_are_rejected(loaded) -> None:
    solution = loaded.accusation_truth().solution
    service = make_service(loaded)

    with pytest.raises(ValueError):
        service.submit("missing", solution.correct_method_id, solution.correct_motive_id)
    with pytest.raises(ValueError):
        service.submit(solution.correct_culprit_id, "missing", solution.correct_motive_id)
    with pytest.raises(ValueError):
        service.submit(solution.correct_culprit_id, solution.correct_method_id, "missing")
    assert service.attempts_used == 0


def test_public_result_never_contains_truth_ids(loaded) -> None:
    solution = loaded.accusation_truth().solution
    service = make_service(loaded)

    result = service.submit(
        solution.correct_culprit_id,
        solution.correct_method_id,
        solution.correct_motive_id,
    )
    payload = json.dumps(dataclasses.asdict(result))

    assert solution.correct_culprit_id not in payload
    assert solution.correct_method_id not in payload
    assert solution.correct_motive_id not in payload
    assert "correct_culprit_id" not in payload


def test_attempt_log_records_the_minute(loaded) -> None:
    solution = loaded.accusation_truth().solution
    wrong_who, _, _ = wrong_ids(loaded)
    clock = FakeClock()
    clock.advance(180)
    service = make_service(loaded, clock=clock)

    service.submit(
        wrong_who,
        solution.correct_method_id,
        solution.correct_motive_id,
    )

    assert service.attempt_log()[0].minute == 3
