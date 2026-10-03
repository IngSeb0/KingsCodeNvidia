"""Create paired-bootstrap comparisons, error analysis, or complementarity status."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kingscode.benchmark_analysis import (write_comparison, write_complementarity_status,
                                        write_error_analysis, write_complementarity, record_selection)
from kingscode.common import ROOT


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["compare", "errors", "complementarity-status", "complementarity", "select"])
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--runs", type=Path, nargs="+")
    parser.add_argument("--variant", help="Exact validated variant; omit for no_selection")
    parser.add_argument("--rationale")
    parser.add_argument("--allow-corpus-change", action="store_true",
                        help="Only for same-commit R0 BM25 runs with verified append-only v0.1 prefix")
    args = parser.parse_args()
    if args.command == "select":
        if args.output or not args.runs or not args.rationale:
            parser.error("select requires --runs and --rationale; output is repository-controlled")
        result = record_selection(args.runs, variant=args.variant, rationale=args.rationale)
    elif not args.output:
        parser.error("--output required")
    elif args.command in {"compare", "complementarity"}:
        if not args.baseline or not args.candidate:
            parser.error("compare requires --baseline and --candidate")
        if args.command == "compare":
            result = write_comparison(args.baseline, args.candidate, args.output,
                                      allow_corpus_change=args.allow_corpus_change)
        else:
            result = write_complementarity(args.baseline, args.candidate, args.output)
    elif args.command == "errors":
        if not args.run:
            parser.error("errors requires --run")
        result = write_error_analysis(args.run, args.output)
    else:
        result = write_complementarity_status(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
