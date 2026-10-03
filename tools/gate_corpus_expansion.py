"""Compare same-commit R0 runs and decide whether corpus expansion cleared C1."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kingscode.benchmark_analysis import load_run
from kingscode.common import ROOT, file_hash, read_json, write_json
from kingscode.retrieval_benchmark import aggregate, bootstrap_reports

TARGET_AREAS = {
    "administrative": "Derecho administrativo",
    "procedural": "Derecho procesal",
    "tax": "Derecho tributario",
}


def _area_rows(rows: list[dict], area: str) -> list[dict]:
    return [row for row in rows if row["question"].get("area") == area]


def assess(baseline_dir: Path, candidate_dir: Path, coverage_path: Path) -> dict:
    baseline, left = load_run(baseline_dir)
    candidate, right = load_run(candidate_dir)
    if (baseline.get("status") != "passed" or candidate.get("status") != "passed"
            or baseline.get("variant") != "R0" or candidate.get("variant") != "R0"
            or baseline.get("split") != "dev" or candidate.get("split") != "dev"
            or baseline.get("git", {}).get("commit") != candidate.get("git", {}).get("commit")
            or baseline.get("benchmark", {}).get("manifest_sha256") != candidate.get("benchmark", {}).get("manifest_sha256")
            or baseline.get("corpus", {}).get("version") != "corpus-v0.1"
            or not (candidate.get("corpus_extension_validation") or {}).get("baseline_passage_prefix_preserved")):
        raise ValueError("C1 requires same-commit R0/dev runs and a pinned lossless v0.1-prefix candidate")
    left_by_id = {row["id"]: row for row in left}
    right_by_id = {row["id"]: row for row in right}
    if set(left_by_id) != set(right_by_id):
        raise ValueError("Baseline and candidate rankings must contain identical IDs")

    overall = {"baseline": baseline["metrics"], "candidate": candidate["metrics"],
               "paired_bootstrap": bootstrap_reports(left, right)}
    area_results = {}
    for code, label in TARGET_AREAS.items():
        a, b = _area_rows(left, label), _area_rows(right, label)
        if not a or {r["id"] for r in a} != {r["id"] for r in b}:
            raise ValueError(f"Benchmark is missing a paired target-area population: {label}")
        area_results[code] = {"area_label": label, "questions": len(a),
                              "baseline": aggregate(a), "candidate": aggregate(b),
                              "paired_bootstrap": bootstrap_reports(a, b)}

    total_bootstrap = overall["paired_bootstrap"]
    overall_ec = total_bootstrap["Evidence Completeness@8"]
    overall_improved = overall_ec["delta"] > 0 and overall_ec["ci_95"][0] > 0
    target_improvements = [name for name, result in area_results.items()
                           if result["paired_bootstrap"]["Evidence Completeness@8"]["delta"] > 0
                           and result["paired_bootstrap"]["Evidence Completeness@8"]["ci_95"][0] > 0]
    no_material_regression = all(total_bootstrap[name]["ci_95"][0] >= 0
                                 for name in ("Recall@10", "MRR@10"))
    coverage_doc = read_json(coverage_path)
    current = coverage_doc.get("report", coverage_doc)
    if current.get("decision_documents_by_authority", {}).get("Consejo de Estado", 0) < 3:
        raise ValueError("Candidate coverage report does not confirm all three official Council of State decisions")
    gate_passed = overall_improved and bool(target_improvements) and no_material_regression
    return {
        "version": "corpus-expansion-c1-gate-v1",
        "status": "PASS" if gate_passed else "NOT_PASSED",
        "benchmark": baseline["benchmark"],
        "git": baseline["git"],
        "baseline_run": {"directory": str(baseline_dir.resolve()), "report_sha256": file_hash(baseline_dir / "report.json"),
                         "corpus": baseline["corpus"]},
        "candidate_run": {"directory": str(candidate_dir.resolve()), "report_sha256": file_hash(candidate_dir / "report.json"),
                          "corpus": candidate["corpus"],
                          "extension_validation": candidate["corpus_extension_validation"]},
        "overall": overall,
        "target_areas": area_results,
        "checks": {
            "overall_evidence_completeness_at_8_improved_with_paired_95ci": overall_improved,
            "at_least_one_undercovered_area_improved_with_paired_95ci": bool(target_improvements),
            "improved_target_areas": target_improvements,
            "recall_at_10_and_mrr_at_10_not_significantly_worse": no_material_regression,
            "council_of_state_sources_in_candidate": 3,
        },
        "coverage_report_sha256": file_hash(coverage_path),
        "holdout_used": False,
        "blind_992_read": False,
        "decision": ("Eligible for a separate sample_50 control after all artifact/hash checks."
                     if gate_passed else "Do not spend GPU time on this corpus candidate; revise corpus or obtain benchmark cases with independently accepted mapped evidence."),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, default=ROOT / "reports/corpus_coverage_final.json")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/corpus_v03_independent_retrieval_comparison.json")
    args = parser.parse_args()
    result = assess(args.baseline, args.candidate, args.coverage)
    write_json(args.output, result)
    print(f"{result['status']}: {args.output}")
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
