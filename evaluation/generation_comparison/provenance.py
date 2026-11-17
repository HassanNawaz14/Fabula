"""Provenance analysis: what did the language model write, and what did Python add?

Reads ONLY what fabula_eval.py already saved (raw model text per call, events.jsonl,
the final bundle). It never runs a model and never changes any file outside
results/analysis/. Run it any time after runs exist:

    python provenance.py --repo ..\\Fabula

Outputs
  results/analysis/provenance.csv        one row per run (both routes)
  results/analysis/provenance_details.json   per-run lists (added facts, novel lines, ...)
  results/analysis/provenance.md         readable summary

Blueprint route (1B) - two questions
  A. How close is the model's outline to Fabula's built-in template generator
     (synthetic_blueprint.py) and vocabulary lists (training_data/skeletons)?
     Each outline line is normalised (ids, locations, numbers and vocabulary
     phrases replaced by placeholders) and compared with the normalised lines
     of 2,000 template outlines. Similarity is DESCRIBED, never scored as failure.
  B. Which parts of the final bundle trace back to the outline, and which did the
     compiler add (NPCs, clues, timeline entries, memory facts)?

Staged route (3B)
  The last accepted raw output of each stage is parsed with the same Pydantic
  models Fabula uses and compared with the final bundle: facts Python added,
  clue links Python changed, and whether 'account_' ever appears in raw text.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
OUT = RESULTS / "analysis"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def setup_import(repo: Path) -> None:
    try:
        import fabula  # noqa: F401
    except ImportError:
        sys.path.insert(0, str(repo / "src"))


# ============================================================ 1B: template similarity
SECTION_HEADERS = {"TIMELINE:", "CLUES:", "KNOWLEDGE:"}


def vocab() -> dict[str, list[str]]:
    from fabula.training_data.skeletons import disappearance, murder, theft

    out: dict[str, list[str]] = {"TARGET": [], "METHOD": [], "MOTIVE": []}
    for mod in (theft, disappearance, murder):
        out["TARGET"] += list(mod.TARGETS)
        out["METHOD"] += list(mod.METHODS)
        out["MOTIVE"] += list(mod.MOTIVES)
    # longest first so a long phrase is replaced before any phrase it contains
    return {k: sorted(set(v), key=len, reverse=True) for k, v in out.items()}


def normalise(line: str, voc: dict[str, list[str]]) -> str:
    s = line.strip()
    for tag, phrases in voc.items():
        for p in phrases:
            s = s.replace(p, f"<{tag}>")
    s = re.sub(r"\bseed_\d+", "seed_<N>", s)
    s = re.sub(r"\bnpc_[a-z0-9_]+?(?=_running|_presence|\b)", "<NPC>", s)
    s = re.sub(r"\bloc_[a-z0-9]+", "<LOC>", s)
    s = re.sub(r"\b(theft|murder|disappearance)\b", "<TYPE>", s)
    s = re.sub(r"\b(cozy|neutral|dark)\b", "<TONE>", s)
    s = re.sub(r"\b(easy|normal|hard)\b", "<DIFF>", s)
    s = re.sub(r"(?<![A-Za-z])\d+(?![A-Za-z])", "<N>", s)
    return re.sub(r"\s+", " ", s)


def template_inventory(n: int = 2000) -> set[str]:
    from fabula.generation.synthetic_blueprint import generate_synthetic_blueprint_sample

    voc = vocab()
    lines: set[str] = set()
    for seed in range(n):
        dsl = generate_synthetic_blueprint_sample(seed)["messages"][2]["content"]
        for line in dsl.splitlines():
            if line.strip() and line.strip() not in SECTION_HEADERS:
                lines.add(normalise(line, voc))
    return lines


LINE_CLASSES = ("template exact", "template, fields omitted", "template, partly changed", "novel")


def _parts(norm: str) -> list[str]:
    return [x.strip() for x in norm.lstrip("- ").split("|") if x.strip()]


def classify_line(line: str, inventory: set[str], voc: dict[str, list[str]]) -> str:
    """exact / a template line with some '|' fields left out / same shape with a
    changed field (e.g. a vocabulary phrase extended) / nothing like any template line."""
    norm = normalise(line, voc)
    if norm in inventory:
        return "template exact"
    parts = set(_parts(norm))
    best = 0.0
    for t in inventory:
        tparts = set(_parts(t))
        if parts and parts < tparts:
            return "template, fields omitted"
        if tparts:
            best = max(best, len(parts & tparts) / max(len(parts), len(tparts)))
    return "template, partly changed" if best >= 0.5 else "novel"


def phrase_origin(value: str, phrases: list[str]) -> str:
    v = value.strip()
    if v in phrases:
        return "vocabulary (verbatim)"
    for p in phrases:
        if v.startswith(p) or p in v:
            return "vocabulary + model extension"
    return "not in vocabulary"


def blueprint_provenance(raw: str, bundle_dir: Path | None, inventory: set[str]) -> dict[str, Any]:
    from fabula.generation.compiler import _identifier
    from fabula.generation.dsl import parse_dsl

    voc = vocab()
    lines = [ln for ln in raw.splitlines() if ln.strip() and ln.strip() not in SECTION_HEADERS]
    classes = {ln.strip(): classify_line(ln, inventory, voc) for ln in lines}
    counts = {c: sum(1 for v in classes.values() if v == c) for c in LINE_CLASSES}
    bp = parse_dsl(raw)
    row: dict[str, Any] = {
        "outline_lines": len(lines),
        "lines_template_exact": counts["template exact"],
        "lines_template_fields_omitted": counts["template, fields omitted"],
        "lines_template_partly_changed": counts["template, partly changed"],
        "lines_novel": counts["novel"],
        "template_exact_share": round(counts["template exact"] / len(lines), 3) if lines else None,
        "target_origin": phrase_origin(bp.cast.victim, voc["TARGET"]),
        "method_origin": phrase_origin(bp.crime.method, voc["METHOD"]),
        "motive_origin": phrase_origin(bp.crime.motive, voc["MOTIVE"]),
        "outline_npc_ids": 1 + len(bp.cast.suspects),
        "outline_timeline_lines": len(bp.timeline),
        "outline_clue_lines": len(bp.clues),
        "outline_knowledge_npcs": len(bp.knowledge),
        "outline_has_difficulty": bool(re.search(r"\|(easy|normal|hard)\|", raw.splitlines()[0] if raw else "")),
    }
    details: dict[str, Any] = {"line_classes": classes}
    if bundle_dir and bundle_dir.is_dir():
        from fabula.schemas import Bundle  # noqa: F401  (load via fabula_eval helper)
        sys.path.insert(0, str(HERE))
        from fabula_eval import load_bundle_dir

        b = load_bundle_dir(bundle_dir)
        outline_clue_ids = {_identifier(c.id, "clue") for c in bp.clues}
        added_clues = [c.id for c in b.clues.clues if _identifier(c.id, "clue") not in outline_clue_ids]
        bundle_clue_ids = {_identifier(c.id, "clue") for c in b.clues.clues}
        dropped_clues = [c for c in sorted(outline_clue_ids) if c not in bundle_clue_ids]
        facts = [f for files in b.npcs.values() for f in files.memory.facts]
        from_knowledge = [f.id for f in facts if "_knows_" in f.id]
        row.update(
            bundle_npcs=len(b.npcs),
            compiler_added_npcs=max(0, len(b.npcs) - row["outline_npc_ids"]),
            bundle_clues=len(b.clues.clues),
            compiler_added_clues=len(added_clues),
            outline_clues_dropped=len(dropped_clues),
            bundle_timeline=len(b.truth.timeline),
            compiler_added_timeline=max(0, len(b.truth.timeline) - len(bp.timeline)),
            bundle_facts=len(facts),
            facts_from_outline_knowledge=len(from_knowledge),
            facts_from_compiler_templates=len(facts) - len(from_knowledge),
        )
        details["compiler_added_clue_ids"] = added_clues
        details["outline_clue_ids_dropped"] = dropped_clues
    return {"row": row, "details": details}


# ============================================================ 3B: raw vs final
def staged_provenance(run_id: str, events: list[dict[str, Any]], bundle_dir: Path | None) -> dict[str, Any]:
    from fabula.schemas import CastDocument, NpcStageOutput, TruthStageOutput, WorldDocument

    calls = [e for e in events if e.get("event") == "model_call" and e.get("run_id") == run_id]
    accepted: dict[tuple[str, str | None], dict[str, Any]] = {}
    attempts: dict[tuple[str, str | None], int] = {}
    for c in calls:
        key = (c["stage"], c.get("npc_id"))
        attempts[key] = attempts.get(key, 0) + 1
        if c.get("raw_file"):
            accepted[key] = c  # the last saved attempt of a stage is the one that was accepted
    raw_texts = {k: Path(v["raw_file"]).read_text(encoding="utf-8") for k, v in accepted.items()
                 if Path(v["raw_file"]).is_file()}
    row: dict[str, Any] = {
        "stages_with_raw_output": len(raw_texts),
        "stage_attempts_total": sum(attempts.values()),
        "stages_retried": sum(1 for n in attempts.values() if n > 1),
        "raw_text_contains_account_prefix": any("account_" in t for t in raw_texts.values()),
    }
    details: dict[str, Any] = {"python_added_facts": [], "python_changed_clues": [], "other_differences": []}
    if not bundle_dir or not bundle_dir.is_dir():
        return {"row": row, "details": details}
    sys.path.insert(0, str(HERE))
    from fabula_eval import load_bundle_dir

    b = load_bundle_dir(bundle_dir)
    culprit = b.truth.solution.correct_culprit_id
    parsed: dict[str, Any] = {}
    for (stage, npc), text in raw_texts.items():
        try:
            if stage == "settings->world":
                parsed["world"] = WorldDocument.model_validate_json(text)
            elif stage == "world->cast":
                parsed["cast"] = CastDocument.model_validate_json(text)
            elif stage == "world+cast->truth+clues":
                parsed["truth"] = TruthStageOutput.model_validate_json(text)
            elif npc:
                parsed[f"npc:{npc}"] = NpcStageOutput.model_validate_json(text)
        except Exception as exc:
            details["other_differences"].append(f"raw {stage} {npc or ''} did not parse: {str(exc)[:120]}")
    if "world" in parsed and parsed["world"] != b.world:
        details["other_differences"].append("world.json differs from raw world output")
    if "truth" in parsed:
        if parsed["truth"].truth != b.truth:
            details["other_differences"].append("truth.json differs from raw truth output")
        raw_clues = {c.id: c for c in parsed["truth"].clues.clues}
        for c in b.clues.clues:
            rc = raw_clues.get(c.id)
            if rc is None:
                details["python_changed_clues"].append({"clue": c.id, "change": "added by Python"})
            elif rc.implies != c.implies:
                details["python_changed_clues"].append(
                    {"clue": c.id, "change": "implies changed",
                     "added_links": [x for x in c.implies if x not in rc.implies]})
    raw_culprit = parsed.get(f"npc:{culprit}")
    for npc_id, files in b.npcs.items():
        raw_npc = parsed.get(f"npc:{npc_id}")
        if raw_npc is None:
            details["other_differences"].append(f"no raw output parsed for {npc_id}")
            continue
        if raw_npc.identity != files.identity:
            details["other_differences"].append(f"identity of {npc_id} differs from raw")
        raw_ids = {f.id for f in raw_npc.memory.facts}
        for f in files.memory.facts:
            if f.id not in raw_ids:
                details["python_added_facts"].append(
                    {"npc": npc_id, "fact_id": f.id, "source": f.source.value, "secret": f.secret, "what": f.what})
    row.update(
        python_added_facts=len(details["python_added_facts"]),
        python_changed_clues=len(details["python_changed_clues"]),
        other_differences=len(details["other_differences"]),
        raw_culprit_had_secret_deed=(
            any(f.source.value == "did" and f.secret for f in raw_culprit.memory.facts) if raw_culprit else None),
        raw_culprit_fact_sources=(
            ";".join(f"{f.source.value}/{'secret' if f.secret else 'open'}" for f in raw_culprit.memory.facts)
            if raw_culprit else None),
    )
    return {"row": row, "details": details}


# ============================================================ main
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", default=str(HERE.parent / "Fabula"))
    p.add_argument("--results", default=str(RESULTS))
    p.add_argument("--steps", help="comma-separated steps (default: all)")
    args = p.parse_args(argv)
    results = Path(args.results)
    out = results / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    setup_import(Path(args.repo).resolve())

    runs = read_jsonl(results / "runs.jsonl")
    if args.steps:
        keep = set(args.steps.split(","))
        runs = [r for r in runs if r["step"] in keep]
    events: list[dict[str, Any]] = []
    for f in (results / "raw").rglob("events.jsonl"):
        events += read_jsonl(f)

    inventory = template_inventory() if any(r["route"] == "fast" for r in runs) else set()
    rows, all_details = [], {}
    for r in runs:
        base = {k: r.get(k) for k in ("run_id", "step", "route", "condition", "seed", "status")}
        bundle = Path(r["bundle_dir"]) if r.get("bundle_dir") else None
        if r["route"] == "fast":
            raws = sorted(Path(r["raw_dir"]).glob("call*_blueprint.txt")) if r.get("raw_dir") else []
            if not raws:
                rows.append({**base, "note": "no raw outline saved"})
                continue
            res = blueprint_provenance(raws[-1].read_text(encoding="utf-8"), bundle, inventory)
        else:
            res = staged_provenance(r["run_id"], events, bundle)
        rows.append({**base, **res["row"]})
        all_details[r["run_id"]] = res["details"]

    keys: list[str] = []
    for row in rows:
        keys += [k for k in row if k not in keys]
    with open(out / "provenance.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    (out / "provenance_details.json").write_text(json.dumps(all_details, indent=2, ensure_ascii=False), encoding="utf-8")

    md = ["# Provenance: model vs Python", "", f"Template inventory: {len(inventory)} distinct normalised outline lines from 2,000 template outlines.", ""]
    fast = [r for r in rows if r["route"] == "fast" and r.get("outline_lines")]
    if fast:
        md += ["## Blueprint route (1B)", "",
               "| run | cond | outline lines | exact / fields omitted / partly changed / novel | target | method | motive | NPCs outline→bundle | clues outline→bundle (added / dropped by compiler) | facts from outline / from compiler templates |",
               "|---|---|---|---|---|---|---|---|---|---|"]
        for r in fast:
            md.append(f"| {r['run_id']} | {r['condition']} | {r['outline_lines']} | {r['lines_template_exact']} / {r['lines_template_fields_omitted']} / {r['lines_template_partly_changed']} / {r['lines_novel']} | "
                      f"{r['target_origin']} | {r['method_origin']} | {r['motive_origin']} | {r['outline_npc_ids']}→{r.get('bundle_npcs')} | "
                      f"{r['outline_clue_lines']}→{r.get('bundle_clues')} ({r.get('compiler_added_clues')} / {r.get('outline_clues_dropped')}) | "
                      f"{r.get('facts_from_outline_knowledge')} / {r.get('facts_from_compiler_templates')} |")
        md += ["", "Outline lines that are not an exact template line (for qualitative review):", ""]
        for rid, d in all_details.items():
            for ln, cls in d.get("line_classes", {}).items():
                if cls != "template exact":
                    md.append(f"- `{rid}` [{cls}]: {ln}")
    staged = [r for r in rows if r["route"] == "staged"]
    if staged:
        md += ["", "## Staged route (3B)", "",
               "| run | status | stages with raw output | attempts | retried stages | 'account_' in raw text | culprit raw had secret deed | facts added by Python | clues changed by Python | other differences |",
               "|---|---|---|---|---|---|---|---|---|---|"]
        for r in staged:
            md.append(f"| {r['run_id']} | {r['status']} | {r.get('stages_with_raw_output')} | {r.get('stage_attempts_total')} | {r.get('stages_retried')} | "
                      f"{r.get('raw_text_contains_account_prefix')} | {r.get('raw_culprit_had_secret_deed')} | {r.get('python_added_facts')} | "
                      f"{r.get('python_changed_clues')} | {r.get('other_differences')} |")
        for rid, d in all_details.items():
            if d.get("python_added_facts") or d.get("python_changed_clues") or d.get("other_differences"):
                md += ["", f"**{rid}**"]
                md += [f"- Python added fact `{f['fact_id']}` to {f['npc']} ({f['source']}, secret={f['secret']}): {f['what']}" for f in d.get("python_added_facts", [])]
                md += [f"- Python changed clue `{c['clue']}`: {c['change']} {c.get('added_links', '')}" for c in d.get("python_changed_clues", [])]
                md += [f"- {x}" for x in d.get("other_differences", [])]
    (out / "provenance.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    print(f"\nWrote {out / 'provenance.csv'}, {out / 'provenance_details.json'}, {out / 'provenance.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
