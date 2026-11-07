"""Audit the SFT stage datasets (train, val, test) against frozen Pydantic contracts and the spoiler firewall."""

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from pydantic import ValidationError

from fabula.schemas.clues import CluesDocument
from fabula.schemas.npc import Identity, Memory
from fabula.schemas.stages import CastDocument
from fabula.schemas.truth import TruthDocument
from fabula.schemas.world import WorldDocument

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "data" / "reports"


def audit_splits() -> dict:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    splits = ["train.jsonl", "val.jsonl", "test.jsonl"]
    
    total_records = 0
    stage_counts: dict[str, int] = {}
    split_counts: dict[str, int] = {}
    errors: list[dict] = []
    spoiler_violations: list[dict] = []
    
    start_time = time.perf_counter()
    
    for split in splits:
        path = PROCESSED_DIR / split
        if not path.exists():
            raise FileNotFoundError(f"Missing dataset file: {path}")
            
        split_records = 0
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                total_records += 1
                split_records += 1
                
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    errors.append({"file": split, "line": idx, "error": f"Invalid JSON: {e}"})
                    continue
                    
                stage = record.get("stage", "UNKNOWN")
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
                
                msgs = record.get("messages", [])
                if len(msgs) != 3:
                    errors.append({"file": split, "line": idx, "error": f"Expected 3 messages, got {len(msgs)}"})
                    continue
                    
                try:
                    user_data = json.loads(msgs[1]["content"])
                    assistant_data = json.loads(msgs[2]["content"])
                except Exception as e:
                    errors.append({"file": split, "line": idx, "error": f"Sub-message JSON decode error: {e}"})
                    continue
                    
                # Schema Validation
                try:
                    if stage == "settings->world":
                        WorldDocument.model_validate(assistant_data)
                    elif stage == "world->cast":
                        CastDocument.model_validate(assistant_data)
                    elif stage == "world+cast->truth+clues":
                        TruthDocument.model_validate(assistant_data["truth"])
                        CluesDocument.model_validate(assistant_data["clues"])
                    elif stage == "world+cast+clues+npc_id->identity+memory":
                        ident = Identity.model_validate(assistant_data["identity"])
                        mem = Memory.model_validate(assistant_data["memory"])
                        if ident.id != mem.npc_id:
                            errors.append({"file": split, "line": idx, "error": f"ID mismatch: {ident.id} != {mem.npc_id}"})
                            
                        # Spoiler Firewall Check
                        has_truth_input = "truth" in user_data
                        has_cover_story = mem.cover_story is not None
                        has_lie = any(f.disclosure.value == "lie" for f in mem.facts)
                        
                        if not has_truth_input and (has_cover_story or has_lie):
                            spoiler_violations.append({
                                "file": split,
                                "line": idx,
                                "npc": ident.id,
                                "error": "Non-culprit prompt contains lie fact or cover story"
                            })
                        elif has_truth_input and not has_cover_story:
                            spoiler_violations.append({
                                "file": split,
                                "line": idx,
                                "npc": ident.id,
                                "error": "Culprit missing cover story"
                            })
                    else:
                        errors.append({"file": split, "line": idx, "error": f"Unknown stage: {stage}"})
                except ValidationError as ve:
                    errors.append({"file": split, "line": idx, "stage": stage, "error": str(ve)[:250]})
                except Exception as ex:
                    errors.append({"file": split, "line": idx, "stage": stage, "error": str(ex)})
                    
        split_counts[split] = split_records

    elapsed = round(time.perf_counter() - start_time, 3)
    
    report = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "duration_seconds": elapsed,
        "total_records_audited": total_records,
        "split_counts": split_counts,
        "stage_counts": stage_counts,
        "schema_errors_count": len(errors),
        "spoiler_violations_count": len(spoiler_violations),
        "status": "PASSED" if (len(errors) == 0 and len(spoiler_violations) == 0) else "FAILED",
        "errors": errors[:20],
        "spoiler_violations": spoiler_violations[:20],
    }
    
    report_path = REPORTS_DIR / "sft_audit_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    report = audit_splits()
    print("=" * 60)
    print(f"SFT AUDIT COMPLETED: STATUS = {report['status']}")
    print(f"Total Records Audited : {report['total_records_audited']}")
    print(f"Split Breakdown       : {report['split_counts']}")
    print(f"Stage Breakdown       : {report['stage_counts']}")
    print(f"Schema Errors         : {report['schema_errors_count']}")
    print(f"Spoiler Violations    : {report['spoiler_violations_count']}")
    print(f"Duration              : {report['duration_seconds']}s")
    print(f"Saved report to       : data/reports/sft_audit_report.json")
    print("=" * 60)

