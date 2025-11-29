import csv
import json
from pathlib import Path
from typing import Dict, Any, Optional


def append_csv(path: Path, row: Dict[str, Any], header: Optional[list] = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = header is not None and (not path.exists())
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header or list(row.keys()))
        if write_header:
            w.writeheader()
        w.writerow(row)


def append_jsonl(path: Path, obj: Dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def log_verification(ocr: Dict[str, Any], user: Dict[str, Any], result: Dict[str, Any],
                     csv_path: Path = Path("logs/verification_runs.csv"),
                     jsonl_path: Path = Path("logs/verification_runs.jsonl")):
    row = {
        "overall_confidence": result.get("overall_confidence"),
        "decision": result.get("decision"),
        **{f"f_{k}": v for k, v in result.get("fields", {}).items()},
        **{f"ocr_{k}": v for k, v in (ocr or {}).items()},
        **{f"user_{k}": v for k, v in (user or {}).items()},
    }
    append_csv(csv_path, row, header=list(row.keys()))
    append_jsonl(jsonl_path, {"ocr": ocr, "user": user, "result": result})
