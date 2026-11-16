"""Tests for Compact Blueprint DSL and Symbolic Compiler."""

from __future__ import annotations

import time

from fabula.generation.compiler import BlueprintCompiler
from fabula.generation.dsl import format_dsl, parse_dsl
from fabula.schemas.validators import validate_bundle

SAMPLE_DSL = """
[CASE:theft|cozy|seed_101]
PREMISE: A priceless antique music box vanishes from the manor drawing room during tea.
CAST: vict:lady_eleanor | culp:npc_butler | susp:npc_maid,npc_gardener,npc_nephew
CRIME: mot:gambling_debt | meth:skeleton_key | scene:loc_library | time:5
TIMELINE:
- 2 | npc_butler | loc_cafe | retrieves duplicate brass key
- 4 | npc_maid | loc_market | delivers tea service
- 5 | npc_butler | loc_library | unlocks display cabinet and takes item
- 7 | npc_nephew | loc_park | observes butler hurriedly walking away
CLUES:
- brass_shaving | loc_library | physical | links:npc_butler | proves:meth
- debt_ledger | loc_cafe | document | links:npc_butler | proves:mot
- muddy_glove | loc_park | trace | red_herring:npc_gardener
KNOWLEDGE:
- npc_maid | sees:npc_butler_near_cabinet | alibi:in_market_at_minute_5
- npc_nephew | sees:npc_butler_in_park | alibi:in_park_with_gardener
- npc_gardener | sees:nephew_at_park | confirms:gardener_alibi
"""


def test_parse_dsl():
    bp = parse_dsl(SAMPLE_DSL)
    assert bp.case_type == "theft"
    assert bp.tone == "cozy"
    assert bp.seed == 101
    assert "music box" in bp.premise
    assert bp.cast.victim == "lady_eleanor"
    assert bp.cast.culprit == "npc_butler"
    assert "npc_maid" in bp.cast.suspects
    assert bp.crime.motive == "gambling_debt"
    assert bp.crime.method == "skeleton_key"
    assert bp.crime.scene == "loc_library"
    assert bp.crime.time == 5
    assert len(bp.timeline) == 4
    assert len(bp.clues) == 3
    assert "npc_maid" in bp.knowledge


def test_format_dsl_roundtrip():
    bp = parse_dsl(SAMPLE_DSL)
    formatted = format_dsl(bp)
    re_parsed = parse_dsl(formatted)
    assert re_parsed.case_type == bp.case_type
    assert re_parsed.seed == bp.seed
    assert re_parsed.crime.motive == bp.crime.motive
    assert len(re_parsed.timeline) == len(bp.timeline)
    assert len(re_parsed.clues) == len(bp.clues)


def test_compiler_generates_valid_bundle():
    bp = parse_dsl(SAMPLE_DSL)
    compiler = BlueprintCompiler(bp, seed=101)
    bundle = compiler.compile()

    # Must be valid per Pydantic and Fabula validators
    issues = validate_bundle(bundle)
    assert issues == []

    # Solvability proof must pass
    assert compiler.verify_solvability(bundle) is True

    # Check structural requirements
    assert len(bundle.world.locations) >= 3
    assert len(bundle.world.npcs) == 5
    assert len(bundle.clues.clues) >= 4
    assert bundle.truth.solution.correct_culprit_id == "npc_butler"

    # The blueprint's cast, timeline, clues, and knowledge reach the bundle.
    assert {npc.id for npc in bundle.world.npcs} >= {
        "npc_butler",
        "npc_maid",
        "npc_gardener",
        "npc_nephew",
    }
    assert any(entry.who == "npc_butler" and entry.t == 5 for entry in bundle.truth.timeline)
    assert any(
        clue.location_id == "loc_library" and "npc_butler_crime_did" in clue.implies
        for clue in bundle.clues.clues
    )
    assert any(
        clue.location_id == "loc_cafe" and "npc_butler_motive" in clue.implies
        for clue in bundle.clues.clues
    )
    assert any(
        fact.id.startswith("npc_maid_knows_") for fact in bundle.npcs["npc_maid"].memory.facts
    )
    assert {state.id for state in bundle.world.accusation_options.methods} >= {"meth_skeleton_key"}


def test_compiler_honors_requested_settings_over_the_blueprint():
    bp = parse_dsl(SAMPLE_DSL)
    compiler = BlueprintCompiler(
        bp,
        seed=101,
        expected_type="murder",
        expected_tone="dark",
        expected_difficulty="hard",
    )
    bundle = compiler.compile()

    assert bundle.world.mystery_type.value == "murder"
    assert bundle.truth.crime.type.value == "murder"
    assert bundle.world.tone.value == "dark"
    assert bundle.world.difficulty.value == "hard"
    assert compiler.verify_solvability(bundle) is True


def test_compiler_parses_optional_difficulty_token():
    parsed = parse_dsl("[CASE:theft|neutral|hard|seed_77]\nPREMISE: test")
    assert parsed.difficulty == "hard"
    assert format_dsl(parsed).splitlines()[0] == "[CASE:theft|neutral|hard|seed_77]"


def test_compiler_latency_under_50ms():
    bp = parse_dsl(SAMPLE_DSL)
    compiler = BlueprintCompiler(bp, seed=42)

    t0 = time.perf_counter()
    bundle = compiler.compile()
    elapsed = time.perf_counter() - t0

    assert validate_bundle(bundle) == []
    # Assert execution took less than 50 ms (0.05 seconds)
    assert elapsed < 0.05, f"Compilation took {elapsed:.4f}s, expected < 0.05s"


def test_compiler_multiple_seeds_and_types():
    for seed in [1, 7, 42, 99, 1234]:
        for ctype in ["theft", "murder", "disappearance"]:
            raw_dsl = f"""
            [CASE:{ctype}|cozy|seed_{seed}]
            PREMISE: A test scenario for seed {seed}.
            CAST: vict:Lord_X | culp:npc_01 | susp:npc_02,npc_03,npc_04,npc_05
            CRIME: mot:greed | meth:poison | scene:loc_library | time:4
            """
            parsed = parse_dsl(raw_dsl)
            compiler = BlueprintCompiler(parsed, seed=seed)
            bundle = compiler.compile()

            issues = validate_bundle(bundle)
            assert issues == [], f"Seed {seed} ({ctype}) had validation issues: {issues}"
            assert compiler.verify_solvability(bundle) is True
