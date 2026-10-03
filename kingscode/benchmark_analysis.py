"""Post-ranking comparison and error analysis for the internal IR benchmark."""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from .common import ROOT, file_hash, read_json, read_jsonl, write_json
from .retrieval_benchmark import benchmark_identity, bootstrap_reports, complementarity

ACTIONS = {
    "corpus_missing": {"owner": "BENCHMARK CURATOR", "action": "verify gold/source coverage; investigate acquisition only with evidence"},
    "wrong_document": {"owner": "RETRIEVAL EXPERIMENTER", "action": "inspect canonical identity, document-level metadata, and document-first retrieval"},
    "correct_document_wrong_passage": {"owner": "RETRIEVAL EXPERIMENTER", "action": "inspect locator matching, chunk boundaries, and near-top ranking"},
    "ranking_failure": {"owner": "RETRIEVAL EXPERIMENTER", "action": "inspect dense/hybrid/reranker once GPU prerequisites exist"},
    "graph_failure": {"owner": "RETRIEVAL EXPERIMENTER", "action": "inspect graph seeding/router/traversal using evidenced relations"},
    "ambiguous_gold": {"owner": "BENCHMARK CURATOR", "action": "fix annotation; do not change retrieval"},
}


def load_run(directory: Path) -> tuple[dict, list[dict]]:
    report = read_json(directory / "report.json")
    rows = read_jsonl(directory / "per_question.jsonl")
    if report.get("status") != "passed":
        raise ValueError("Only passed runs can be analyzed")
    if report.get("per_question_sha256") != file_hash(directory / "per_question.jsonl"):
        raise ValueError("Per-question artifact hash mismatch")
    if not rows or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Run must contain nonempty unique question IDs")
    return report, rows


def _compatible_runs(baseline, candidate, *, allow_corpus_change: bool = False):
    if baseline["benchmark"]["manifest_sha256"] != candidate["benchmark"]["manifest_sha256"]:
        raise ValueError("Cannot compare runs from different benchmark manifests")
    if baseline["split"] != candidate["split"]:
        raise ValueError("Cannot compare different splits")
    if baseline["corpus"] != candidate["corpus"]:
        if not allow_corpus_change:
            raise ValueError("Cannot compare different corpus snapshots without the explicit append-only comparison gate")
        pinned = benchmark_identity()["manifest"]["corpus"]
        candidate_proof = candidate.get("corpus_extension_validation") or {}
        if (baseline["variant"] != "R0" or candidate["variant"] != "R0"
                or baseline["corpus"].get("version") != pinned.get("version")
                or not candidate_proof.get("baseline_passage_prefix_preserved")
                or candidate_proof.get("baseline_passages_sha256") != pinned.get("passages.jsonl")
                or baseline.get("git", {}).get("commit") != candidate.get("git", {}).get("commit")
                or baseline.get("source_identity") != candidate.get("source_identity")
                or baseline.get("config") != candidate.get("config")):
            raise ValueError("Corpus comparison requires same-commit R0 runs and a verified lossless baseline prefix")


def write_complementarity(baseline_dir: Path, candidate_dir: Path, output: Path) -> dict:
    baseline, left = load_run(baseline_dir)
    candidate, right = load_run(candidate_dir)
    _compatible_runs(baseline, candidate)
    if baseline["variant"] != "R0" or candidate["variant"] != "R1-QWEN":
        raise ValueError("This comparison requires R0 vs R1-QWEN dense-only")
    if candidate.get("execution", {}).get("verified_real_backend") is not True:
        raise ValueError("Complementarity requires a verified real dense run")
    result = {"status": "analyzed", "split": baseline["split"],
              "benchmark_manifest_sha256": baseline["benchmark"]["manifest_sha256"],
              "reports": {"baseline": file_hash(baseline_dir / "report.json"),
                          "candidate": file_hash(candidate_dir / "report.json")},
              "by_k": {str(k): complementarity(left, right, k=k) for k in (1, 3, 5, 8, 10)}}
    write_json(output, result)
    return result


def record_selection(run_dirs: list[Path], *, variant: str | None, rationale: str) -> dict:
    """Record a human validation decision, never auto-select or consume holdout."""
    if not rationale.strip() or len(run_dirs) < 2:
        raise ValueError("Selection requires rationale and at least two validation runs")
    loaded = [(path, *load_run(path)) for path in run_dirs]
    manifest_sha = benchmark_identity()["manifest_sha256"]
    reports = {}
    for path, report, rows in loaded:
        if (report["split"] != "validation" or report["benchmark"]["manifest_sha256"] != manifest_sha
                or report.get("config", {}).get("diagnostic")):
            raise ValueError("Selection accepts only non-diagnostic validation of the current manifest")
        if report["variant"] in reports:
            raise ValueError("Supply exactly one run per variant")
        if report["variant"] != "R0" and report.get("execution", {}).get("verified_real_backend") is not True:
            raise ValueError("Neural selection requires verified real weights")
        _compatible_runs(loaded[0][1], report)
        reports[report["variant"]] = (path, report, rows)
    if "R0" not in reports:
        raise ValueError("Include the R0 validation baseline")
    baseline_rows = reports["R0"][2]
    evidence = {}
    for name, (path, report, rows) in reports.items():
        evidence[name] = {"directory": str(path.resolve()), "report_sha256": file_hash(path / "report.json"),
                          "metrics": report["metrics"], "subgroups": report["subgroups"],
                          "peak_vram_bytes": report.get("peak_vram_bytes"),
                          "initialization_seconds": report.get("initialization_seconds"),
                          "retrieval_total_seconds": report.get("retrieval_total_seconds"),
                          "bootstrap_vs_r0": bootstrap_reports(baseline_rows, rows)}
    # Display trade-offs, never use a weighted score. Missing costs prevent a
    # dominance claim. Secondary metrics and CIs remain available to reviewers.
    directions = {"Evidence Completeness@8": 1, "Recall@10": 1, "MRR@10": 1,
                  "nDCG@10": 1, "latency_p95_ms": -1, "retrieved_tokens": -1}
    frontier = []
    for name, item in evidence.items():
        def dominates(other):
            a, b = other["metrics"], item["metrics"]
            if any(a.get(m) is None or b.get(m) is None for m in directions):
                return False
            return (all(sign * a[m] >= sign * b[m] for m, sign in directions.items())
                    and any(sign * a[m] > sign * b[m] for m, sign in directions.items()))
        if not any(dominates(other) for key, other in evidence.items() if key != name):
            frontier.append(name)
    if variant is not None and variant not in reports:
        raise ValueError("Selected variant must have a supplied validation run")
    result = {"status": "selected" if variant else "no_selection", "selection_split": "validation",
              "variant": variant, "benchmark_manifest_sha256": manifest_sha,
              "rationale": rationale, "decision_method": "explicit human decision; no automatic ranking",
              "evidence": evidence, "pareto_frontier": sorted(frontier),
              "pareto_axes": directions, "pareto_note": "Point estimates, not statistical dominance; inspect CIs and VRAM separately.",
              "execution_identity": reports[variant][1].get("execution_identity") if variant else None,
              "holdout_executed": False}
    if variant and not result["execution_identity"]:
        raise ValueError("Selected run lacks an exact execution identity; rerun validation with this harness")
    output = ROOT / "reports/benchmark/selection/selected_config.json"
    if output.exists():
        previous = read_json(output)
        if previous.get("status") == "selected":
            raise FileExistsError("A selected configuration is immutable; do not retune after selection")
    write_json(output, result)
    return result


def compare(baseline_dir: Path, candidate_dir: Path, *, allow_corpus_change: bool = False) -> dict:
    baseline, base_rows = load_run(baseline_dir)
    candidate, candidate_rows = load_run(candidate_dir)
    _compatible_runs(baseline, candidate, allow_corpus_change=allow_corpus_change)
    return {"version": "benchmark-comparison-v1", "benchmark": benchmark_identity(),
            "baseline": {"variant": baseline["variant"], "directory": baseline["directory"], "metrics": baseline["metrics"]},
            "candidate": {"variant": candidate["variant"], "directory": candidate["directory"], "metrics": candidate["metrics"]},
            "corpus_comparison": {"enabled": baseline["corpus"] != candidate["corpus"],
                                  "baseline_corpus": baseline["corpus"], "candidate_corpus": candidate["corpus"],
                                  "candidate_extension_validation": candidate.get("corpus_extension_validation")},
            "bootstrap": bootstrap_reports(base_rows, candidate_rows),
            "note": "If a confidence interval includes zero, the paired difference is inconclusive."}


def error_analysis(directory: Path) -> dict:
    report, rows = load_run(directory)
    by_class, by_area, by_tag, examples = Counter(), defaultdict(Counter), defaultdict(Counter), defaultdict(list)
    for row in rows:
        failure = row["failure"]
        if failure == "success":
            continue
        # The benchmark's generated exact gold has already been corpus-verified.
        # A miss is a retrieval failure; ambiguous-gold is reserved for later
        # human-authored cases and never fabricated here.
        mapped = failure
        by_class[mapped] += 1
        by_area[row["question"]["area"]][mapped] += 1
        for tag in row["question"]["tags"]:
            by_tag[tag][mapped] += 1
        if len(examples[mapped]) < 10:
            examples[mapped].append({"id": row["id"], "question": row["question"]["question"],
                                     "area": row["question"]["area"], "tags": row["question"]["tags"],
                                     "retrieved": row["retrieved"][:3], "recommendation": ACTIONS.get(mapped)})
    return {"version": "benchmark-error-analysis-v1", "benchmark": benchmark_identity(),
            "run": {"variant": report["variant"], "split": report["split"], "directory": report["directory"]},
            "counts": dict(sorted(by_class.items())),
            "by_area": {area: dict(sorted(c.items())) for area, c in sorted(by_area.items())},
            "by_tag": {tag: dict(sorted(c.items())) for tag, c in sorted(by_tag.items())},
            "representative_cases": dict(examples), "owner_action": ACTIONS,
            "policy": "Failures drive targeted investigation; no blind corpus expansion."}


def write_comparison(baseline_dir: Path, candidate_dir: Path, output: Path, *, allow_corpus_change: bool = False) -> dict:
    result = compare(baseline_dir, candidate_dir, allow_corpus_change=allow_corpus_change)
    write_json(output, result)
    return result


def write_error_analysis(directory: Path, output: Path) -> dict:
    result = error_analysis(directory)
    write_json(output, result)
    return result


def write_complementarity_status(output: Path) -> dict:
    result = {"version": "benchmark-complementarity-status-v1", "benchmark": benchmark_identity(),
              "status": "GPU_BLOCKED", "executed_pairs": [],
              "user_reported_bge_m3_old_official_sample": {"Recall@5": 0.4100, "Recall@10": 0.4593,
                  "verification": "No underlying report/config/index exists in this repository; retained as user-reported only, not reproduced evidence."},
              "required_pairs": ["BM25 vs BGE-M3", "BM25 vs Qwen3-Embedding-0.6B"],
              "required_outputs": ["both_hit", "bm25_only", "dense_only", "both_miss", "intersection", "union", "oracle_union_recall", "examples"],
              "blockers": ["local CPU-only environment", "Qwen dense index absent", "BGE-M3 lacks approved immutable model lock and local loader/index implementation"],
              "next_step": "On approved GPU, run same-ID dense variants then call kingscode.retrieval_benchmark.complementarity at k=1,3,5,8,10."}
    write_json(output, result)
    return result
