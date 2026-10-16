import pytest

from fabula.schemas import Bundle, Disclosure, MysteryType, validate_bundle
from fabula.training_data import generate_skeleton

ALL_TYPES = [MysteryType.THEFT, MysteryType.DISAPPEARANCE, MysteryType.MURDER]


@pytest.mark.parametrize("mystery_type", ALL_TYPES)
def test_one_hundred_seeds_per_type_validate(mystery_type: MysteryType) -> None:
    for seed in range(100):
        bundle = generate_skeleton(mystery_type, seed)
        issues = validate_bundle(bundle)
        assert issues == [], f"{mystery_type} seed {seed}: {issues}"


@pytest.mark.parametrize("mystery_type", ALL_TYPES)
def test_same_seed_is_identical(mystery_type: MysteryType) -> None:
    first = generate_skeleton(mystery_type, 42).model_dump(mode="json")
    second = generate_skeleton(mystery_type, 42).model_dump(mode="json")
    assert first == second


@pytest.mark.parametrize("mystery_type", ALL_TYPES)
def test_different_seeds_vary(mystery_type: MysteryType) -> None:
    first = generate_skeleton(mystery_type, 42).model_dump(mode="json")
    second = generate_skeleton(mystery_type, 43).model_dump(mode="json")
    assert first != second


@pytest.mark.parametrize("mystery_type", ALL_TYPES)
def test_only_culprit_holds_true_account(mystery_type: MysteryType) -> None:
    for seed in range(20):
        bundle = generate_skeleton(mystery_type, seed)
        culprit = bundle.truth.solution.correct_culprit_id
        for npc_id, files in bundle.npcs.items():
            if npc_id == culprit:
                assert files.memory.cover_story is not None
                assert any(f.disclosure == Disclosure.LIE for f in files.memory.facts)
            else:
                assert files.memory.cover_story is None
                assert all(f.disclosure != Disclosure.LIE for f in files.memory.facts)


def test_tone_and_difficulty_overrides_are_honoured() -> None:
    bundle = generate_skeleton(MysteryType.THEFT, 7, tone="dark", difficulty="hard")
    assert bundle.world.tone == "dark"
    assert bundle.world.difficulty == "hard"


def test_scenario_ids_are_unique_per_type_and_seed() -> None:
    seen = set()
    for mystery_type in ALL_TYPES:
        for seed in range(10):
            scenario_id = generate_skeleton(mystery_type, seed).world.scenario_id
            assert scenario_id not in seen
            seen.add(scenario_id)


def test_skeletons_are_renderable_bundle_shapes() -> None:
    bundle = generate_skeleton(MysteryType.MURDER, 3)
    assert 3 <= len(bundle.world.locations) <= 4
    assert 5 <= len(bundle.world.npcs) <= 6
    assert 4 <= len(bundle.clues.clues) <= 6
    assert Bundle.model_validate(bundle.model_dump(mode="json")) == bundle
