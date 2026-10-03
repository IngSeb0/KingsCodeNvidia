"""Run or record a KingsCode internal retrieval benchmark variant."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kingscode.common import ROOT
from kingscode.retrieval_benchmark import GPU_VARIANT_PREREQUISITES, record_gpu_blocked, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True, choices=["R0", "R0-GRAPH-AUTO-DIAGNOSTIC", "R0-GRAPH-ON-DIAGNOSTIC",
                        "R6-BM25-DIAGNOSTIC", "R7-BM25-DIAGNOSTIC", "R8-BM25-DIAGNOSTIC", *GPU_VARIANT_PREREQUISITES])
    parser.add_argument("--split", required=True, choices=["dev", "validation", "holdout"])
    parser.add_argument("--corpus", type=Path, default=ROOT / "corpus")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--allow-holdout", action="store_true")
    parser.add_argument("--holdout-purpose", choices=["predeclared_baseline", "post_selection_confirmation"])
    parser.add_argument("--record-gpu-blocked", action="store_true")
    parser.add_argument("--allow-corpus-additions", action="store_true",
                        help="R0 CPU only: compare a lossless append-only candidate to pinned v0.1 on dev/validation")
    parser.add_argument("--base-run", type=Path, help="Explicit R2-QWEN validation base for R3-R8")
    args = parser.parse_args()
    if args.record_gpu_blocked:
        result = record_gpu_blocked(args.variant, args.split, output_root=args.output_root,
                                    allow_holdout=args.allow_holdout, holdout_purpose=args.holdout_purpose)
    else:
        result = run(args.variant, args.split, corpus=args.corpus, output_root=args.output_root,
                     allow_holdout=args.allow_holdout, holdout_purpose=args.holdout_purpose, base_run=args.base_run,
                     allow_corpus_additions=args.allow_corpus_additions)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
