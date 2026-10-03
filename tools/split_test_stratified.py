"""Deterministically split the blind file by area and format for parallel GPUs.

Only reads row IDs plus public runtime metadata (format/area); it does not print
or save question text in a split manifest. Output lines keep each input JSON row
byte-for-byte, normalizing only line terminators.

    python tools/split_test_stratified.py data/test_992.jsonl 2
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def split_rows(source: Path, parts: int, *, force: bool = False) -> dict:
    source = Path(source)
    if source.name.casefold() != "test_992.jsonl":
        raise ValueError("This operational splitter accepts only data/test_992.jsonl")
    if parts < 2 or parts > 16:
        raise ValueError("parts must be between 2 and 16")
    raw_lines = [line for line in source.read_bytes().splitlines() if line.strip()]
    groups: dict[tuple[str, str], list[tuple[int, bytes, str]]] = defaultdict(list)
    seen_ids = set()
    for index, raw in enumerate(raw_lines):
        row = json.loads(raw.decode("utf-8-sig"))
        item_id = str(row.get("id") or "")
        if not item_id or item_id in seen_ids:
            raise ValueError("Blind file has a missing or duplicate ID")
        seen_ids.add(item_id)
        fmt = str(row.get("formato") or row.get("format") or "(sin formato)")
        area = str(row.get("area") or "(sin área)")
        groups[(fmt, area)].append((index, raw, item_id))

    assignments: list[list[tuple[int, bytes, str]]] = [[] for _ in range(parts)]
    loads = [0] * parts
    stratum_counts: list[Counter] = [Counter() for _ in range(parts)]
    cursor = 0
    for stratum in sorted(groups):
        rows = groups[stratum]
        for row_index, raw, item_id in rows:
            lightest = min(loads)
            choices = [(cursor + offset) % parts for offset in range(parts)]
            target = next(part for part in choices if loads[part] == lightest)
            assignments[target].append((row_index, raw, item_id))
            loads[target] += 1
            stratum_counts[target][f"{stratum[0]} | {stratum[1]}"] += 1
            cursor = (target + 1) % parts

    output_paths = [source.with_name(f"{source.stem}.parte{part}.jsonl") for part in range(1, parts + 1)]
    if not force:
        existing = [path for path in output_paths if path.exists()]
        if existing:
            raise FileExistsError(f"Refusing to overwrite generated split file(s): {', '.join(map(str, existing))}; pass --force")
    outputs = []
    for part, rows in enumerate(assignments, start=1):
        output = output_paths[part - 1]
        ordered = sorted(rows)
        output.write_bytes(b"".join(raw.rstrip(b"\r\n") + b"\n" for _, raw, _ in ordered))
        outputs.append({"path": output.name, "rows": len(rows),
                        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                        "strata": dict(sorted(stratum_counts[part - 1].items()))})
    return {"source": source.name, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "rows": len(raw_lines), "unique_ids": len(seen_ids), "parts": outputs,
            "stratification_fields": ["formato/format", "area"],
            "blind_question_text_written_to_manifest": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("parts", type=int)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(json.dumps(split_rows(args.source, args.parts, force=args.force), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
