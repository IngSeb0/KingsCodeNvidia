"""Validate (and optionally merge) the blind-set delivery before the 15:00 deadline.

    python tools/validate_test_submission.py --test data/test_992.jsonl submissions.jsonl
    python tools/validate_test_submission.py --test data/test_992.jsonl --merge parte1.jsonl parte2.jsonl --out submissions.jsonl

Uses the official `scripts/evaluate.py::validate` (same function the jury runs: ids, formats,
required fields, pasajes_recuperados, missing items) plus `schema/submission.schema.json`.
`--split test` of the evaluator needs the answer key, which teams do not have; this is the
format check the organizers ask for. --merge concatenates the per-PC halves (no row is edited),
checks there are no duplicates and writes them in the test file's id order.
Exit code 0 only if there are zero problems.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate import validate  # noqa: E402


def read(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8-sig").splitlines() if l.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", type=Path, required=True)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--out", type=Path)
    ap.add_argument("files", type=Path, nargs="+")
    args = ap.parse_args(argv)
    order = [r["id"] for r in read(args.test)]
    rows = [r for f in args.files for r in read(f)]
    if args.merge:
        by_id = {}
        for r in rows:
            if r["id"] in by_id:
                print(f"STOP: id {r['id']} repetido entre las partes"); return 1
            by_id[r["id"]] = r
        rows = [by_id[i] for i in order if i in by_id]
        out = args.out or Path("submissions.jsonl")
        with out.open("w", encoding="utf-8", newline="\n") as stream:
            for r in rows:
                stream.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Unido: {out} ({len(rows)} filas)")
        target = out
    else:
        target = args.files[0]
    problems = validate(rows, set(order))
    try:
        from jsonschema import Draft202012Validator
        schema = Draft202012Validator(json.loads((ROOT / "schema/submission.schema.json").read_text(encoding="utf-8")))
        for r in rows:
            for err in schema.iter_errors(r):
                problems.append(f"item {r.get('id')}: esquema: {err.message[:120]}")
    except ImportError:
        print("(jsonschema no instalado: solo se aplico evaluate.validate)")
    abst = sum(bool(r.get("abstencion")) for r in rows)
    print(json.dumps({"archivo": str(target), "filas": len(rows), "esperadas": len(order), "abstenciones": abst,
                      "problemas": len(problems), "primeros": problems[:10],
                      "sha256": hashlib.sha256(Path(target).read_bytes()).hexdigest()}, ensure_ascii=False, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
