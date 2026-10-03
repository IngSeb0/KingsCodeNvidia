"""Leakage-safe evaluator for the KingsCode internal legal IR benchmark.

Questions and gold live in separate files. Ranking functions receive only a
retrieval-safe question string; gold is loaded strictly after all rankings are
captured. The module is deterministic and contains no official-sample access.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import math
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time

from .benchmark_builder import BENCHMARK_ROOT, FORBIDDEN_QUESTION_KEYS, _schema_validator
from .common import ROOT, file_hash, read_json, read_jsonl, write_json, write_jsonl
from .metadata import canonical_document_id, canonical_fragment_id
from .metadata_experiments import run_experiment
from .retrieval import Retriever, tokenize

BENCHMARK_RUN_VERSION = "kingscode-ir-run-v2"
MAX_K = 10

# R1--R8 planned variants requiring assets / GPU state unavailable locally.
GPU_VARIANT_PREREQUISITES = {
    "R1-QWEN": ["RTX 4090 CUDA/BF16 validated", "Qwen dense snapshot verified", "corpus/index/dense.npy built"],
    "R1-BGE": ["approved immutable BGE-M3 model lock (not present)", "BGE-M3 loader/index implementation", "RTX 4090 CUDA/BF16 validated"],
    "R2-QWEN": ["R1-QWEN prerequisites", "fixed RRF constant 60 and candidate_k 30"],
    "R2-BGE": ["R1-BGE prerequisites", "fixed RRF constant 60 and candidate_k 30"],
    "R3": ["explicitly chosen R2-QWEN validation run", "Qwen reranker snapshot verified", "RTX 4090 CUDA/BF16 validated"],
    "R4": ["R3 prerequisites", "deterministic B graph router available"],
    "R5": ["R3 prerequisites"],
    "R6": ["R3 prerequisites; metadata soft prior only"],
    "R7": ["R3 prerequisites; document-first ablation"],
    "R8": ["R3 prerequisites; content collapse + document diversification ablation"],
}


def benchmark_manifest() -> dict:
    return read_json(BENCHMARK_ROOT / "manifests" / "benchmark_manifest.json")


def benchmark_identity() -> dict:
    manifest_path = BENCHMARK_ROOT / "manifests" / "benchmark_manifest.json"
    return {"manifest_sha256": file_hash(manifest_path), "manifest": benchmark_manifest()}


def _safe_questions(split: str) -> list[dict]:
    rows = read_jsonl(BENCHMARK_ROOT / "questions" / f"{split}.jsonl")
    for q in rows:
        if FORBIDDEN_QUESTION_KEYS & q.keys():
            raise ValueError("Gold/evaluation fields are forbidden in question input")
    return rows


def _gold_after_ranking(split: str) -> dict[str, dict]:
    return {g["id"]: g for g in read_jsonl(BENCHMARK_ROOT / "gold" / f"{split}.jsonl")}


def retrieval_input(question_record: dict) -> str:
    """The only object sent into retrieval: no tags, area, IDs or gold fields."""
    if FORBIDDEN_QUESTION_KEYS & question_record.keys():
        raise ValueError("Attempt to pass gold/evaluation field into retrieval")
    value = question_record.get("question")
    if not isinstance(value, str):
        raise TypeError("Question input must contain plain text")
    return value


def _passage_view(passage: dict) -> dict:
    """Small, deterministic ranking record retaining provenance but no gold."""
    return {"passage_id": passage["passage_id"],
            "canonical_document_id": canonical_document_id(passage),
            "canonical_fragment_id": canonical_fragment_id(passage),
            "clean_start": passage.get("clean_start"), "clean_end": passage.get("clean_end"),
            "characters": len(passage.get("text", "")),
            "tokens": len(tokenize(passage.get("text", ""))),
            "score": passage.get("score"),
            "retrieval": passage.get("retrieval", {}),
            "experiment": passage.get("experiment")}


def _executed_config(variant: str) -> dict:
    from .benchmark_runtime import EXECUTABLE, variant_config
    if variant in EXECUTABLE:
        return variant_config(variant)
    base = {"mode": "bm25", "rerank": False, "candidate_k": 30, "k_metrics": 10, "seed": 0}
    if variant == "R0":
        return {**base, "graph_mode": "off", "diagnostic": False}
    if variant == "R0-GRAPH-AUTO-DIAGNOSTIC":
        return {**base, "graph_mode": "auto", "diagnostic": True, "diagnostic_reason": "BM25 graph ablation, not R4"}
    if variant == "R0-GRAPH-ON-DIAGNOSTIC":
        return {**base, "graph_mode": "on", "diagnostic": True, "diagnostic_reason": "BM25 graph ablation, not R5"}
    if variant == "R6-BM25-DIAGNOSTIC":
        return {**base, "graph_mode": "off", "diagnostic": True, "experiment": "R6", "base_mode": "bm25", "effective_parameters": {"candidate_multiplier": 4}, "diagnostic_reason": "Not R3-based"}
    if variant == "R7-BM25-DIAGNOSTIC":
        return {**base, "graph_mode": "off", "diagnostic": True, "experiment": "R7", "base_mode": "bm25", "effective_parameters": {"doc_pool": 24}, "diagnostic_reason": "Not R3-based"}
    if variant == "R8-BM25-DIAGNOSTIC":
        return {**base, "graph_mode": "off", "diagnostic": True, "experiment": "R8", "base_mode": "bm25", "effective_parameters": {"collapse_level": "content", "diversify_level": "document", "max_per_group": 2}, "diagnostic_reason": "Not R3-based"}
    raise ValueError(f"No executable configuration for {variant}")


def _run_one(retriever: Retriever, variant: str, text: str, k: int) -> list[dict]:
    if variant == "R0":
        return retriever.retrieve(text, k, "off")
    if variant in {"R0-GRAPH-AUTO-DIAGNOSTIC", "R0-GRAPH-ON-DIAGNOSTIC"}:
        return retriever.retrieve(text, k, "auto" if "AUTO" in variant else "on")
    # These CPU calls deliberately have diagnostic names; they are not reported
    # as R6/R7/R8 because their contractual base is R3, which is GPU-blocked.
    if variant in {"R6-BM25-DIAGNOSTIC", "R7-BM25-DIAGNOSTIC", "R8-BM25-DIAGNOSTIC"}:
        return run_experiment(variant[:2], retriever, text, k)
    raise ValueError(f"{variant} is not executable in the local CPU benchmark runner")


def _direct_gold(gold: dict) -> set[str]:
    return {item["canonical_fragment_id"] for item in gold["evidence"] if item["relevance"] == "direct"}


def _supporting_gold(gold: dict) -> set[str]:
    return {item["canonical_fragment_id"] for item in gold["evidence"] if item["relevance"] == "supporting"}


def _matches_at_k(result: list[dict], gold: dict, k: int) -> tuple[set[str], set[str], list[str]]:
    direct, supporting = _direct_gold(gold), _supporting_gold(gold)
    found_direct, found_supporting, ids = set(), set(), []
    for p in result[:k]:
        fid = canonical_fragment_id(p)
        ids.append(fid)
        if fid in direct:
            found_direct.add(fid)
        if fid in supporting:
            found_supporting.add(fid)
    return found_direct, found_supporting, ids


def per_question_metrics(result: list[dict], gold: dict, *, max_k: int = MAX_K) -> dict:
    """Compute hand-auditable metrics for a single ranked result."""
    direct = _direct_gold(gold)
    docs = set(gold["gold_document_ids"])
    if not direct or not docs:
        raise ValueError("Gold must contain direct evidence and a document")
    values: dict[str, float | int | bool | None] = {}
    for k in (1, 3, 5, 8, 10):
        found, _, _ = _matches_at_k(result, gold, k)
        found_docs = {canonical_document_id(p) for p in result[:k]} & docs
        values[f"Recall@{k}"] = len(found) / len(direct)
        values[f"Passage Recall@{k}"] = len(found) / len(direct)
        values[f"Document Recall@{k}"] = len(found_docs) / len(docs)
        values[f"Evidence Completeness@{k}"] = float(found == direct)
    first = next((rank for rank, p in enumerate(result[:10], 1) if canonical_fragment_id(p) in direct), None)
    values["MRR@10"] = 1 / first if first else 0.0
    # AP@10: a gold fragment has relevance once; repeated same fragment is not a new hit.
    seen, ap_sum = set(), 0.0
    for rank, p in enumerate(result[:10], 1):
        fid = canonical_fragment_id(p)
        if fid in direct and fid not in seen:
            seen.add(fid)
            ap_sum += len(seen) / rank
    values["MAP@10"] = ap_sum / len(direct)
    gains, seen = [], set()
    supporting = _supporting_gold(gold)
    for p in result[:10]:
        fid = canonical_fragment_id(p)
        gain = 0.0
        if fid not in seen:
            gain = 1.0 if fid in direct else (0.5 if fid in supporting else 0.0)
            seen.add(fid)
        gains.append(gain)
    dcg = sum(gain / math.log2(rank + 2) for rank, gain in enumerate(gains))
    ideal = [1.0] * len(direct) + [0.5] * len(supporting)
    idcg = sum(gain / math.log2(rank + 2) for rank, gain in enumerate(ideal[:10]))
    values["nDCG@10"] = dcg / idcg if idcg else 0.0
    first_doc = canonical_document_id(result[0]) if result else None
    # A missing rank-1 cannot improve a wrong-document metric. Empty rankings
    # are therefore mismatches and are also visible through retrieved_passages.
    values["Document Mismatch Rate"] = float(first_doc not in docs)
    # Span metrics are evaluated against exact source intervals.
    gold_spans = gold.get("gold_spans", [])
    matched_spans, retrieved_offset_count = set(), 0
    for p in result[:10]:
        start, end, fid = p.get("clean_start"), p.get("clean_end"), canonical_fragment_id(p)
        if start is None or end is None:
            continue
        retrieved_offset_count += 1
        for idx, span in enumerate(gold_spans):
            if span["canonical_fragment_id"] == fid and start < span["clean_end"] and end > span["clean_start"]:
                matched_spans.add(idx)
    values["Span Recall"] = len(matched_spans) / len(gold_spans) if gold_spans else None
    values["Span Precision"] = len(matched_spans) / retrieved_offset_count if retrieved_offset_count else None
    values["retrieved_passages"] = len(result[:10])
    values["retrieved_characters"] = sum(len(p.get("text", "")) for p in result[:10])
    values["retrieved_tokens"] = sum(len(tokenize(p.get("text", ""))) for p in result[:10])
    values["unique_documents"] = len({canonical_document_id(p) for p in result[:10]})
    fids = [canonical_fragment_id(p) for p in result[:10]]
    values["duplicate_fragment_count"] = len(fids) - len(set(fids))
    return values


def _mean(rows: list[dict], name: str) -> float | None:
    values = [r["metrics"][name] for r in rows if r["metrics"].get(name) is not None]
    return sum(values) / len(values) if values else None


def aggregate(rows: list[dict]) -> dict:
    names = ["Recall@1", "Recall@3", "Recall@5", "Recall@8", "Recall@10", "MRR@10", "MAP@10", "nDCG@10",
             "Document Recall@10", "Document Mismatch Rate", "Passage Recall@10", "Evidence Completeness@8",
             "Evidence Completeness@10", "Span Recall", "Span Precision", "retrieved_passages", "retrieved_characters",
             "retrieved_tokens", "unique_documents", "duplicate_fragment_count"]
    latencies = sorted(r["latency_ms"] for r in rows)
    result = {name: _mean(rows, name) for name in names}
    result.update({"questions": len(rows),
                   "latency_p50_ms": statistics.median(latencies) if latencies else None,
                   "latency_p95_ms": latencies[max(0, math.ceil(len(latencies) * .95) - 1)] if latencies else None})
    return result


def subgroup_metrics(rows: list[dict]) -> dict:
    groups: dict[str, dict[str, list[dict]]] = {"area": defaultdict(list), "tag": defaultdict(list),
                                                 "explicit_vs_semantic": defaultdict(list), "evidence_cardinality": defaultdict(list)}
    for row in rows:
        q = row["question"]
        groups["area"][q["area"]].append(row)
        for tag in q["tags"]:
            groups["tag"][tag].append(row)
        groups["explicit_vs_semantic"]["semantic" if "SEMANTIC" in q["tags"] else "explicit"].append(row)
        groups["evidence_cardinality"]["multi_evidence" if "MULTI_EVIDENCE" in q["tags"] else "single_evidence"].append(row)
    return {group: {name: aggregate(items) for name, items in sorted(values.items())} for group, values in groups.items()}


def classify_failure(result: list[dict], candidate_result: list[dict], gold: dict, tags: list[str]) -> str:
    direct, docs = _direct_gold(gold), set(gold["gold_document_ids"])
    top_fids = {canonical_fragment_id(p) for p in result[:10]}
    if direct <= top_fids:
        return "success"
    candidate_fids = {canonical_fragment_id(p) for p in candidate_result}
    if not direct & candidate_fids:
        # Corpus/gold integrity is validated separately; missing candidate evidence
        # at candidate_k is a retrieval failure, not automatic corpus absence.
        if {canonical_document_id(p) for p in result[:10]} & docs:
            return "correct_document_wrong_passage"
        return "graph_failure" if "GRAPH" in tags else "wrong_document"
    return "ranking_failure"


def _git(command: list[str]) -> str | None:
    try:
        return subprocess.check_output(command, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).rstrip("\r\n")
    except Exception:
        return None


def _verify_declared_hashes(corpus: Path, *, allow_corpus_additions: bool = False) -> dict | None:
    """Verify the pinned baseline, or an explicit lossless append-only extension."""
    declared = benchmark_manifest()
    if declared.get("schema_sha256") != file_hash(BENCHMARK_ROOT / "benchmark.schema.json"):
        raise ValueError("Benchmark schema hash differs from manifest")
    for split, expected in declared.get("splits", {}).items():
        if expected.get("question_sha256") != file_hash(BENCHMARK_ROOT / "questions" / f"{split}.jsonl"):
            raise ValueError(f"Question split hash differs from manifest: {split}")
        if expected.get("gold_sha256") != file_hash(BENCHMARK_ROOT / "gold" / f"{split}.jsonl"):
            raise ValueError(f"Gold split hash differs from manifest: {split}")
    corpus_manifest = read_json(corpus / "manifest.json")
    for name, expected in corpus_manifest["hashes"].items():
        if file_hash(corpus / name) != expected:
            raise ValueError(f"Corpus file hash differs: {name}")
    if file_hash(corpus / "index/bm25.json") != corpus_manifest["bm25_sha256"]:
        raise ValueError("BM25 file hash differs")
    mismatches = []
    for name, expected in declared.get("corpus", {}).items():
        if name in {"version", "bm25_sha256"}:
            actual = corpus_manifest.get(name)
        else:
            actual = corpus_manifest.get("hashes", {}).get(name)
        if actual != expected:
            mismatches.append(name)
    if not mismatches:
        return None
    if not allow_corpus_additions:
        raise ValueError(f"Corpus snapshot differs from benchmark manifest: {', '.join(mismatches)}")
    if corpus.resolve() == (ROOT / "corpus").resolve():
        raise ValueError("The baseline corpus itself cannot be treated as an additions candidate")

    # Candidate runs are restricted to R0 BM25 diagnostics on dev/validation.
    # Resolve the base only from the candidate's recorded input inventory, then
    # re-hash it against the benchmark snapshot before checking byte-prefix.
    inputs = corpus_manifest.get("inputs") or {}
    base_matches = []
    for input_name, entry in inputs.items():
        base = Path(input_name)
        if not base.is_absolute():
            base = ROOT / base
        if base.name.casefold() == "test_992.jsonl":
            raise ValueError("Blind competitive file is forbidden as a corpus base")
        base_manifest_path = base / "manifest.json"
        if not base_manifest_path.is_file():
            continue
        base_manifest = read_json(base_manifest_path)
        if (base_manifest.get("version") != declared.get("corpus", {}).get("version")
                or entry.get("version") != base_manifest.get("version")
                or entry.get("manifest_sha256") != file_hash(base_manifest_path)
                or entry.get("passages_sha256") != file_hash(base / "passages.jsonl")):
            continue
        exact = True
        for name, expected in declared.get("corpus", {}).items():
            if name == "version":
                continue
            actual = base_manifest.get("bm25_sha256") if name == "bm25_sha256" else base_manifest.get("hashes", {}).get(name)
            if actual != expected:
                exact = False
                break
            path = base / ("index/bm25.json" if name == "bm25_sha256" else name)
            if file_hash(path) != expected:
                exact = False
                break
        if exact:
            base_matches.append((base, base_manifest))
    if len(base_matches) != 1:
        raise ValueError("Candidate must record exactly one intact v0.1 input matching the benchmark snapshot")
    base, base_manifest = base_matches[0]
    base_passages = base / "passages.jsonl"
    candidate_passages = corpus / "passages.jsonl"
    if not candidate_passages.read_bytes().startswith(base_passages.read_bytes()):
        raise ValueError("Candidate does not preserve every baseline passage byte-for-byte in original order")
    if corpus_manifest.get("status") != "diagnostic_not_competitive_freeze":
        raise ValueError("Append-only corpus runs must remain diagnostic, not a competitive freeze")
    return {"status": "verified_append_only_extension", "baseline_version": base_manifest["version"],
            "baseline_passages_sha256": file_hash(base_passages),
            "baseline_manifest_sha256": file_hash(base / "manifest.json"),
            "candidate_passages_sha256": file_hash(candidate_passages),
            "candidate_bm25_sha256": file_hash(corpus / "index/bm25.json"),
            "baseline_passage_prefix_preserved": True,
            "candidate_document_count": corpus_manifest.get("n_documentos"),
            "candidate_indexed_passages": corpus_manifest.get("n_indexed")}


def _holdout_declaration() -> dict:
    path = BENCHMARK_ROOT / "manifests" / "holdout_access.json"
    if not path.exists():
        raise PermissionError("Missing immutable holdout access declaration")
    declaration = read_json(path)
    if declaration.get("benchmark_manifest_sha256") != file_hash(BENCHMARK_ROOT / "manifests" / "benchmark_manifest.json"):
        raise PermissionError("Holdout declaration belongs to a different benchmark manifest")
    return declaration


def _holdout_was_consumed(variant: str, manifest_sha256: str) -> bool:
    reports = ROOT / "reports" / "benchmark"
    if not reports.exists():
        return False
    for path in reports.rglob("report.json"):
        try:
            report = read_json(path)
        except Exception:
            continue
        if report.get("status") == "passed" and report.get("split") == "holdout" and report.get("variant") == variant and report.get("benchmark", {}).get("manifest_sha256") == manifest_sha256:
            return True
    return False


def _assert_holdout_policy(split: str, variant: str, allow_holdout: bool, holdout_purpose: str | None) -> None:
    if split != "holdout":
        return
    if not allow_holdout or holdout_purpose not in {"predeclared_baseline", "post_selection_confirmation"}:
        raise PermissionError("Holdout is protected; pass allowed purpose explicitly")
    declaration = _holdout_declaration()
    manifest_sha = declaration["benchmark_manifest_sha256"]
    if _holdout_was_consumed(variant, manifest_sha):
        raise PermissionError("This holdout variant was already consumed for the pinned benchmark")
    if holdout_purpose == "predeclared_baseline":
        allowed = {(item["variant"], item["split"]) for item in declaration.get("predeclared", [])}
        if (variant, split) not in allowed:
            raise PermissionError("Variant is not predeclared for holdout baseline")
    else:
        selection_path = ROOT / "reports" / "benchmark" / "selection" / "selected_config.json"
        if not selection_path.exists():
            raise PermissionError("Post-selection holdout requires a committed validation selection record")
        selection = read_json(selection_path)
        if selection.get("status") != "selected" or selection.get("selection_split") != "validation" or selection.get("variant") != variant or selection.get("benchmark_manifest_sha256") != manifest_sha:
            raise PermissionError("Selection record does not authorize this holdout variant")


def _source_identity() -> dict:
    files = [ROOT / "kingscode" / name for name in [
        "benchmark_builder.py", "retrieval_benchmark.py", "benchmark_runtime.py", "benchmark_analysis.py", "neural.py", "model_assets.py", "retrieval.py", "metadata.py", "metadata_experiments.py", "diversify.py", "reasoning/routing.py", "reasoning/query.py", "reasoning/policy.py", "reasoning/legal.py"]]
    files += [ROOT / "tools" / "evaluate_retrieval_benchmark.py", ROOT / "config" / "experiment_matrix.json"]
    return {path.relative_to(ROOT).as_posix(): file_hash(path) for path in files if path.exists()}


def _assert_clean_tree() -> None:
    dirty = _git(["git", "status", "--porcelain", "--untracked-files=all"])
    if dirty is None:
        raise RuntimeError("Cannot verify git source state")
    # A run may create prior immutable artifacts below reports/benchmark. They do
    # not change the evaluator/source snapshot and are intentionally allowed so
    # dev, validation and predeclared baseline runs can coexist. Any other
    # tracked or untracked change blocks a reproducible run.
    offenders = []
    for line in dirty.splitlines():
        path = line[3:].replace("\\", "/") if len(line) >= 4 else line
        if not path.startswith("reports/benchmark/"):
            offenders.append(line)
    if offenders:
        raise RuntimeError("Benchmark runs require a clean source tree; commit non-report changes first: " + "; ".join(offenders))


def run(variant: str, split: str, *, corpus: Path | None = None, output_root: Path | None = None,
        allow_holdout: bool = False, holdout_purpose: str | None = None, base_run: Path | None = None,
        allow_corpus_additions: bool = False) -> dict:
    """Run verified real retrieval, keeping all labels behind the ranking boundary."""
    from .benchmark_runtime import EXECUTABLE, NeuralRuntime, execution_identity, validate_base_run
    if split not in {"dev", "validation", "holdout"}:
        raise ValueError("split must be dev, validation or holdout")
    if split == "holdout" and output_root is not None:
        raise PermissionError("Holdout reports must use the repository-controlled default output root")
    _assert_holdout_policy(split, variant, allow_holdout, holdout_purpose)
    if allow_corpus_additions and (split not in {"dev", "validation"} or variant not in {"R0", "R0-GRAPH-AUTO-DIAGNOSTIC", "R0-GRAPH-ON-DIAGNOSTIC"}):
        raise PermissionError("Append-only corpus comparison is limited to CPU BM25 variants on dev/validation")
    corpus = corpus or ROOT / "corpus"
    corpus_extension_validation = _verify_declared_hashes(corpus, allow_corpus_additions=allow_corpus_additions)
    _assert_clean_tree()
    if variant in {"R1-BGE", "R2-BGE"}:
        return record_gpu_blocked(variant, split, output_root=output_root,
                                  allow_holdout=allow_holdout, holdout_purpose=holdout_purpose)
    config = _executed_config(variant)
    neural = variant in EXECUTABLE
    identity = benchmark_identity()
    manifest = read_json(corpus / "manifest.json")
    corpus_id = {"version": manifest["version"], "hashes": manifest["hashes"], "bm25_sha256": manifest["bm25_sha256"]}
    source = _source_identity()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = (output_root or ROOT / "reports/benchmark" / variant.lower().replace("-", "_")) / f"{stamp}-{split}"
    directory.mkdir(parents=True, exist_ok=False)
    report = {"version": BENCHMARK_RUN_VERSION, "status": "running", "variant": variant, "split": split,
              "holdout_purpose": holdout_purpose if split == "holdout" else None,
              "git": {"commit": _git(["git", "rev-parse", "HEAD"]), "branch": _git(["git", "branch", "--show-current"])},
              "corpus": corpus_id, "benchmark": identity, "source_identity": source,
              "config": config, "model": None,
              "corpus_extension_validation": corpus_extension_validation,
              "hardware": {"platform": platform.platform(), "python": sys.version, "cuda": False},
              "directory": str(directory.resolve()), "completed_rankings": 0}
    runtime, rankings = None, []
    started = time.perf_counter()
    try:
        if neural and variant not in {"R1-QWEN", "R2-QWEN"}:
            report["base_r2"] = validate_base_run(base_run, identity["manifest_sha256"], corpus_id)
        init_start = time.perf_counter()
        if neural:
            runtime = NeuralRuntime(corpus, config)
            report["execution"] = runtime.record()
            if report["execution"].get("verified_real_backend") is not True:
                raise RuntimeError("UNVERIFIED_BACKEND: refusing a passed GPU run")
            report["execution_identity"] = execution_identity(config, runtime.assets, source)
            if "base_r2" in report:
                base_id = report["base_r2"]["execution_identity"]
                now_id = report["execution_identity"]
                for name in ("neural_config", "dense_sha256", "dense_meta_sha256", "source_identity"):
                    if base_id[name] != now_id[name]:
                        raise ValueError(f"R2 base configuration drift: {name}")
                if base_id["models"]["encoder"] != now_id["models"]["encoder"]:
                    raise ValueError("R2 base encoder snapshot drift")
            report["model"] = runtime.assets["models"]
            report["hardware"].update(cuda=True, **report["execution"]["hardware"])
            retrieve = runtime.retrieve
        else:
            retriever = Retriever(corpus, mode="bm25", candidate_k=30, graph_budget=10)
            retrieve = lambda text, k: _run_one(retriever, variant, text, k)
            report["execution_identity"] = {"config": config, "source_identity": source}
        report["initialization_seconds"] = time.perf_counter() - init_start
        if split == "holdout" and holdout_purpose == "post_selection_confirmation":
            selection = read_json(ROOT / "reports/benchmark/selection/selected_config.json")
            if selection.get("execution_identity") != report["execution_identity"]:
                raise PermissionError("Selected execution configuration differs from holdout configuration")
        questions = _safe_questions(split)
        retrieval_started = time.perf_counter()
        for question in questions:
            text = retrieval_input(question)
            if runtime:
                runtime.sync()
            question_start = time.perf_counter()
            candidate = retrieve(text, 30)
            if runtime:
                runtime.sync()
            rankings.append({"question": question, "latency_ms": (time.perf_counter() - question_start) * 1000,
                             "result": candidate[:10], "candidate_result": candidate})
        report["retrieval_total_seconds"] = time.perf_counter() - retrieval_started
        report["completed_rankings"] = len(rankings)
        if runtime:
            report["execution"] = runtime.record()
            report["peak_vram_bytes"] = report["execution"]["peak_vram_bytes"]
        else:
            report["peak_vram_bytes"] = None
        # No parsed gold is available to the backend, including during setup.
        gold_by_id = _gold_after_ranking(split)
        rows = []
        for ranking in rankings:
            question, gold = ranking["question"], gold_by_id[ranking["question"]["id"]]
            metrics = per_question_metrics(ranking["result"], gold)
            matched_by_k = {str(k): sorted(_matches_at_k(ranking["result"], gold, k)[0]) for k in (1, 3, 5, 8, 10)}
            rows.append({"id": question["id"], "question": question, "latency_ms": ranking["latency_ms"],
                         "metrics": metrics, "gold_direct_count": len(_direct_gold(gold)),
                         "matched_direct_fragment_ids_by_k": matched_by_k,
                         "retrieved": [_passage_view(p) for p in ranking["result"]],
                         "failure": classify_failure(ranking["result"], ranking["candidate_result"], gold, question["tags"])})
        write_jsonl(directory / "per_question.jsonl", rows)
        report.update(status="passed", metrics=aggregate(rows), subgroups=subgroup_metrics(rows),
                      failure_taxonomy=dict(sorted(Counter(row["failure"] for row in rows).items())),
                      per_question_sha256=file_hash(directory / "per_question.jsonl"),
                      label_boundary="all rankings completed before gold file was loaded")
    except Exception as exc:
        report.update(status="failed", completed_rankings=len(rankings),
                      error={"type": type(exc).__name__, "message": str(exc)})
        # No aggregate metrics or partial success artifact on failed runs.
    finally:
        report["total_seconds"] = time.perf_counter() - started
        write_json(directory / "report.json", report)
    return report


def record_gpu_blocked(variant: str, split: str, *, output_root: Path | None = None,
                       allow_holdout: bool = False, holdout_purpose: str | None = None) -> dict:
    if split == "holdout" and output_root is not None:
        raise PermissionError("Holdout reports must use the repository-controlled default output root")
    _assert_holdout_policy(split, variant, allow_holdout, holdout_purpose)
    _verify_declared_hashes(ROOT / "corpus")
    _assert_clean_tree()
    if variant not in GPU_VARIANT_PREREQUISITES:
        raise ValueError("Only planned GPU variants can be recorded as GPU_BLOCKED")
    output_root = output_root or (ROOT / "reports" / "benchmark" / variant.lower().replace("-", "_"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = output_root / f"{stamp}-{split}"
    directory.mkdir(parents=True, exist_ok=False)
    commands = ["python tools/prepare_gpu_environment.py --diagnose --output reports/gpu_diagnostic.json",
                "python tools/prepare_gpu_environment.py --configure-retrieval",
                "python tools/member_a.py dense"]
    if variant == "R1-BGE" or variant == "R2-BGE":
        commands.append("BLOCKED: approve a separate immutable BGE-M3 model lock and loader/index implementation; do not use an unpinned revision.")
    else:
        commands.append("python tools/evaluate_retrieval_benchmark.py --variant " + variant + " --split " + split)
    report = {"version": BENCHMARK_RUN_VERSION, "status": "GPU_BLOCKED", "variant": variant, "split": split,
              "holdout_purpose": holdout_purpose if split == "holdout" else None,
              "reason": "Required prerequisites are not approved/available, or operator explicitly recorded a blocked run. No metrics claimed.",
              "prerequisites": GPU_VARIANT_PREREQUISITES[variant], "exact_next_commands": commands,
              "benchmark": benchmark_identity(), "source_identity": _source_identity(),
              "git": {"commit": _git(["git", "rev-parse", "HEAD"]), "branch": _git(["git", "branch", "--show-current"])} }
    write_json(directory / "report.json", report)
    return report


def complementarity(left_rows: list[dict], right_rows: list[dict], *, k: int = 10) -> dict:
    """Same-ID complementarity; computes oracle union evidence recovery."""
    left, right = {r["id"]: r for r in left_rows}, {r["id"]: r for r in right_rows}
    if set(left) != set(right):
        raise ValueError("Complementarity requires the same question IDs")
    if len(left) != len(left_rows) or len(right) != len(right_rows):
        raise ValueError("Duplicate question IDs are forbidden")
    counts = Counter({k: 0 for k in ("both_hit", "bm25_only", "dense_only", "both_miss")})
    examples = {k: [] for k in counts}
    union_values = []
    for qid in sorted(left):
        a, b = left[qid], right[qid]
        ahit = a["metrics"][f"Recall@{k}"] > 0
        bhit = b["metrics"][f"Recall@{k}"] > 0
        label = "both_hit" if ahit and bhit else "bm25_only" if ahit else "dense_only" if bhit else "both_miss"
        counts[label] += 1
        if label in examples and len(examples[label]) < 10:
            examples[label].append(qid)
        # Exact oracle union over gold fragments recorded after the retrieval
        # boundary. This cannot be reconstructed from aggregate recall alone.
        union_hits = set(a.get("matched_direct_fragment_ids_by_k", {}).get(str(k), [])) | set(b.get("matched_direct_fragment_ids_by_k", {}).get(str(k), []))
        gold_count = a.get("gold_direct_count")
        if gold_count != b.get("gold_direct_count") or not gold_count:
            raise ValueError("Complementarity rows carry inconsistent gold cardinality")
        union_values.append(len(union_hits) / gold_count)
    total = len(left)
    return {"k": k, "counts": dict(counts), "intersection": counts["both_hit"] / total if total else None,
            "union": (counts["both_hit"] + counts["bm25_only"] + counts["dense_only"]) / total if total else None,
            "qwen_only": counts["dense_only"], "oracle_union_recall": sum(union_values) / total if total else None, "examples": examples}


def paired_bootstrap(baseline: list[float], candidate: list[float], *, seed: int = 0, resamples: int = 10_000) -> dict:
    """Deterministic paired bootstrap confidence interval for candidate-baseline."""
    if len(baseline) != len(candidate) or not baseline:
        raise ValueError("Paired bootstrap requires equal non-empty vectors")
    deltas = [c - b for b, c in zip(baseline, candidate)]
    rng, n = random.Random(seed), len(deltas)
    samples = sorted(sum(deltas[rng.randrange(n)] for _ in range(n)) / n for _ in range(resamples))
    def percentile(p: float) -> float:
        return samples[min(len(samples) - 1, max(0, math.ceil(p * len(samples)) - 1))]
    return {"estimate_baseline": sum(baseline) / n, "estimate_candidate": sum(candidate) / n,
            "delta": sum(deltas) / n, "ci_95": [percentile(.025), percentile(.975)],
            "bootstrap_seed": seed, "resamples": resamples, "paired_questions": n}


def bootstrap_reports(baseline_rows: list[dict], candidate_rows: list[dict], *, metrics: tuple[str, ...] = ("Evidence Completeness@8", "Recall@10", "MRR@10")) -> dict:
    by_a, by_b = {r["id"]: r for r in baseline_rows}, {r["id"]: r for r in candidate_rows}
    if set(by_a) != set(by_b):
        raise ValueError("Bootstrap requires identical question IDs")
    return {metric: paired_bootstrap([by_a[i]["metrics"][metric] for i in sorted(by_a)], [by_b[i]["metrics"][metric] for i in sorted(by_a)]) for metric in metrics}
