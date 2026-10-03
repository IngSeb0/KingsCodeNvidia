"""Preserved Gate 1B smoke plus explicit, separate Gate 2 decoder commands."""
from pathlib import Path
import argparse
import json
import os
import sys
import subprocess
from datetime import datetime, timezone
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kingscode.common import ROOT
from kingscode.reasoning.experiments import run_experiment


def positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def graph_budget_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("must be an integer from 0 to 100") from exc
    if not 0 <= parsed <= 100:
        raise argparse.ArgumentTypeError("must be an integer from 0 to 100")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["smoke", "decoder-smoke", "sample", "bakeoff", "batch", "verify", "plan"])
    parser.add_argument("--input", type=Path, help="batch/verify/plan: questions JSONL (public fields only are read)")
    parser.add_argument("--run-dir", type=Path, help="batch: checkpoint/output directory")
    parser.add_argument("--fresh", action="store_true", help="batch: refuse to resume an existing run directory")
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--show-answers", action="store_true",
                        help="batch: print each question and generated answer to stderr as it completes")
    parser.add_argument("--retrieval-mode", choices=["base", "option", "plan", "option_plan"], default="option")
    parser.add_argument("--plans", type=Path, help="plan mode: frozen reports/query_plans/<id> directory (replay)")
    parser.add_argument("--k", type=int, default=8)
    parser.add_argument("--candidate-k", type=positive_int, default=30,
                        help="retrieval candidate depth before reranking (default: 30)")
    parser.add_argument("--reranker-batch-size", type=positive_int, default=2,
                        help="Qwen reranker GPU forward batch size (default: 2; test 1 or 2 on 24 GB GPUs)")
    parser.add_argument("--graph-policy", choices=["router", "off", "auto", "on"], default="router")
    parser.add_argument("--graph-budget", type=graph_budget_int, default=10,
                        help="graph-expanded passage limit before reranking (0 disables expansion; default: 10, range: 0-100)")
    parser.add_argument("--synthetic", type=int, help="batch: rehearsal with the input repeated to N questions with new ids")
    parser.add_argument("--delivered", type=Path, help="verify: submissions.jsonl to compare against")
    parser.add_argument("--only", help="verify: comma-separated ids to regenerate")
    parser.add_argument("--exact-locator", action="store_true", help="A's exact locator (resolves only the original question)")
    parser.add_argument("--retriever-mode", choices=["bm25", "dense", "hybrid"], default="bm25")
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--reranker-score-cache", action="store_true",
                        help="opt-in exact LRU reuse of repeated Qwen reranker question/passage scores within one run")
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--fixture-evidence", action="store_true",
                        help="batch/verify: official fixture passages instead of a corpus (reproducibility smoke only, not a score)")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--retrieval-freeze", type=Path)
    parser.add_argument("--precision", choices=["bf16", "int8", "int4"], default="bf16")
    parser.add_argument("--oom-record", type=Path)
    parser.add_argument("--allow-optional", action="store_true")
    parser.add_argument("--prompt-version", choices=["v3", "v4", "v6", "v7", "v8", "v9"], default="v3",
                        help="batch/verify: v3 default, v4 format fixes, v6 legal reasoning, v7 concise, v8 coverage-calibrated candidate")
    parser.add_argument("--citation-fill", action="store_true",
                        help="batch/verify: complete up to 5 verified citations with top-ranked evidence (semi_open/multiple_choice only)")
    parser.add_argument("--cite-mentions", type=int, default=0, metavar="N",
                        help="batch/verify: up to N body-level citations of norms NAMED in retrieved passages (official support rule); semi_open/MC only")
    parser.add_argument("--fit-passages", action="store_true",
                        help="decoder: shorten the longest passages in the prompt (head kept) before dropping any")
    parser.add_argument("--max-context", type=int, default=None, metavar="N",
                        help="decoder context window in tokens (default 8192 from the bakeoff config; up to 32768)")
    parser.add_argument("--doc-cap", type=int, default=0, metavar="N",
                        help="batch/verify: fetch 10 passages and keep at most N per document (0 = off, default)")
    parser.add_argument("--native-option-fusion", action="store_true",
                        help="batch/verify: fuse MC option views inside A before one Q0-based rerank; experimental and opt-in")
    parser.add_argument("--retrieval-text-mode", choices=["literal", "context"], default="literal",
                        help="context uses structural metadata only for search; evidence/citations remain literal")
    parser.add_argument("--dense-index-dir", type=Path,
                        help="isolated dense-index directory; required for dense/hybrid context mode")
    parser.add_argument("--embedding-instruction-profile", choices=["baseline", "smallest_authoritative_primary_source", "direct_primary_source", "exact_rule_and_article", "minimal_evidence"], default="baseline")
    parser.add_argument("--reranker-instruction-profile", choices=["baseline", "direct_primary_law_support", "direct_support", "rule_exception_holding", "source_and_article"], default="baseline")
    parser.add_argument("--plan-roles", help="plan: comma-separated Q1,Q2,Q3 subset; replay frozen plans")
    parser.add_argument("--option-support", action="store_true",
                        help="MC-only auxiliary Q+option cosine scores on final evidence; never chooses the answer")
    parser.add_argument("--constrained-json", action="store_true",
                        help="optional XGrammar JSON syntax/type constraints; strict parser and citation guard remain")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan only; no CUDA, weights or evaluation")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "smoke":
        if args.model or args.precision != "bf16" or args.oom_record or args.retrieval_freeze or args.allow_optional or args.dry_run:
            parser.error("smoke retains the exact Gate 1B dummy contract; use only --config/--output-root")
        result = run_experiment(config_path=args.config or ROOT / "config/reasoning.json",
                                output_root=args.output_root or ROOT / "reports/member_b")
        print(json.dumps({"status": result["status"], "fingerprint": result["fingerprint"], "paths": result["paths"],
                      "submission_sha256": result["submission_sha256"], "metrics": result["metrics"],
                      "official_total": result["official_evaluation"]["total_automatico"],
                      "neural_modules_loaded": result["neural_modules_loaded"]}, ensure_ascii=False, indent=2))
        return 0
    if args.command in {"batch", "verify", "plan"}:
        return run_b_command(args, parser)
    from kingscode.generation.config import load_bakeoff, select_decoder
    config_path = args.config or ROOT / "config/decoder_bakeoff.json"
    cfg = load_bakeoff(config_path)
    if args.command != "bakeoff" and not args.model:
        parser.error("--model is required")
    if args.command == "bakeoff" and (args.model or args.precision != "bf16" or args.oom_record):
        parser.error("bakeoff varies only decoder in BF16; run precision fallbacks as separate sample experiments")
    models = ([args.model] if args.model else [name for name, c in cfg["candidates"].items() if c["enabled"] or args.allow_optional])
    selected = {name: select_decoder(name, cfg, allow_optional=args.allow_optional) for name in models}
    freeze = args.retrieval_freeze or ROOT / cfg["retrieval_freeze"]
    if args.dry_run:
        print(json.dumps({"status": "prepared_not_executed", "command": args.command, "candidates": selected,
                          "retrieval_freeze": str(freeze), "precision": args.precision,
                          "prompt_version": cfg["prompt_version"], "generation": cfg["generation"],
                          "gpu_validated": False}, ensure_ascii=False, indent=2))
        return 0
    output_root = args.output_root or ROOT / "reports/decoders"
    if args.command != "bakeoff":
        from kingscode.generation.experiments import run_generation
        result = run_generation(args.model, mode=args.command, config_path=config_path, freeze_path=freeze,
                                output_root=output_root, precision=args.precision, oom_record=args.oom_record,
                                allow_optional=args.allow_optional)
        print(json.dumps({k: result.get(k) for k in ("status", "paths", "metrics", "error", "official_evaluation")}, ensure_ascii=False, indent=2))
        return int(result["status"] != "passed")
    # New process per decoder: retrieval evidence stays fixed, VRAM is released.
    from kingscode.common import file_hash, write_json
    from kingscode.generation.retrieval_experiments import load_freeze
    load_freeze(freeze)
    freeze_hash = file_hash(freeze)
    results = []
    for name in models:
        if file_hash(freeze) != freeze_hash:
            raise ValueError("Frozen evidence changed during bakeoff")
        command = [sys.executable, str(Path(__file__).resolve()), "sample", "--model", name,
                   "--config", str(config_path), "--retrieval-freeze", str(freeze), "--output-root", str(output_root)]
        if args.allow_optional:
            command.append("--allow-optional")
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        try:
            result = json.loads(proc.stdout)
        except ValueError:
            result = {"status": "failed", "error": {"code": "CHILD_PROCESS_FAILED", "returncode": proc.returncode}}
        results.append({"model": name, "returncode": proc.returncode, **result})
    report = {"status": "passed" if all(r["status"] == "passed" and r["returncode"] == 0 for r in results) else "failed",
              "retrieval_freeze_sha256": freeze_hash, "precision": "bf16", "results": results}
    path = output_root / ("bakeoff-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    write_json(path, report)
    print(json.dumps({"report": str(path), **report}, ensure_ascii=False, indent=2))
    return int(report["status"] != "passed")


def _read_items(path: Path, skip_options: bool = False) -> list[tuple]:
    """(id, question text) only: the planner never sees options, labels or gold."""
    items = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            record = json.loads(line)
            if skip_options and record.get("formato") == "multiple_choice" and record.get("opciones"):
                continue  # option_plan answers these with option views: no plan needed
            items.append((record["id"], record.get("pregunta", record.get("question"))))
    return items


class _RerankSafeRetriever:
    """A's QwenReranker raises on any query+passage pair over max_length (no silent
    truncation). Without this, that single question would fall back to abstention.
    Here that query is answered with A's own pre-rerank order instead: deterministic
    (same input -> same path) and marked in every passage's retrieval metadata.
    Same retrieve() signature as A's, so the pipeline still detects query_views."""

    def __init__(self, retriever):
        self.inner, self.corpus_hash = retriever, retriever.corpus_hash

    def retrieve(self, question, k=8, graph_mode="auto", query_views=None):
        started = perf_counter()
        try:
            return self.inner.retrieve(question, k, graph_mode, query_views=query_views)
        except ValueError as exc:
            if "exceeds max_length" not in str(exc):
                raise
            reranker, self.inner.reranker = self.inner.reranker, None
            try:
                passages = self.inner.retrieve(question, k, graph_mode, query_views=query_views)
            finally:
                self.inner.reranker = reranker
            recovery_ms = round((perf_counter() - started) * 1000, 3)
            for p in passages:
                p.setdefault("retrieval", {})["rerank_skipped"] = "input_over_max_length"
                profile = p["retrieval"].get("profile")
                if isinstance(profile, dict):
                    profile["reranker_status"] = "skipped_input_over_max_length"
                    profile["rerank_skip_recovery_ms"] = recovery_ms
                    profile["total_ms"] = recovery_ms
                    profile["candidate_pairs_when_skipped"] = profile.get("candidate_count")
            return passages


def _pipeline(args):
    # Callers (tests, other tools) may pass a partial Namespace: fill every missing option
    # with its parser default so new flags never break older call sites.
    for name, value in vars(build_parser().parse_args(["batch"])).items():
        if not hasattr(args, name):
            setattr(args, name, value)
    from kingscode.reasoning import DummyDecoder, Pipeline, RetrieverGraphRouter
    from kingscode.reasoning.plan_store import PlanStore
    if getattr(args, "plan_roles", None) and args.retrieval_mode != "plan":
        raise ValueError("--plan-roles requires --retrieval-mode plan")
    if args.option_support and args.fixture_evidence:
        raise ValueError("--option-support needs the real dense corpus index; fixture evidence is incompatible")
    instruction_profiles = json.loads((ROOT / "config/retrieval_instruction_profiles.json").read_text(encoding="utf-8"))
    embedding_instruction = instruction_profiles["embedding"][args.embedding_instruction_profile]
    reranker_instruction = instruction_profiles["reranker"][args.reranker_instruction_profile]
    adapter = RetrieverGraphRouter()
    base_retriever = None
    if args.fixture_evidence:
        from copy import deepcopy
        fixtures = json.loads((ROOT / "tests/fixtures/member_b_official_passages.json").read_text(encoding="utf-8"))

        class _FixtureRetriever:
            corpus_hash = "fixture:tests/fixtures/member_b_official_passages.json"

            def retrieve(self, question, k=8, graph_mode="auto"):
                return deepcopy(fixtures[:k])
        retriever = _FixtureRetriever()
    else:
        from kingscode import Retriever
        base_retriever = Retriever(args.corpus, mode=args.retriever_mode, rerank=args.rerank, graph_router=adapter,
                              candidate_k=args.candidate_k, reranker_batch_size=args.reranker_batch_size,
                              graph_budget=args.graph_budget, exact_locator=args.exact_locator,
                              retrieval_text_mode=args.retrieval_text_mode, dense_index_dir=args.dense_index_dir,
                              embedding_instruction=(embedding_instruction if args.embedding_instruction_profile != "baseline" else None),
                              reranker_instruction=(reranker_instruction if args.reranker_instruction_profile != "baseline" else None),
                              reranker_score_cache=args.reranker_score_cache)
        retriever = base_retriever
        if args.rerank:
            retriever = _RerankSafeRetriever(retriever)
        if args.option_support and base_retriever.dense is None:
            raise ValueError("--option-support requires --retriever-mode dense or hybrid")
    decoder = DummyDecoder()
    if args.model:
        from kingscode.generation.hf_decoder import HFDecoder
        selected_prompt = ("grounded-formats-v5-option-support" if args.option_support
                           else f"grounded-formats-{args.prompt_version}")
        decoder = HFDecoder(args.model, precision=args.precision, allow_optional=args.allow_optional,
                            prompt_version=selected_prompt, constrained_json=args.constrained_json,
                            max_context_tokens=args.max_context, fit_passages=args.fit_passages)
    plans = PlanStore(args.plans) if args.plans else None
    plan_roles = tuple(part.strip() for part in getattr(args, "plan_roles", None).split(",") if part.strip()) if getattr(args, "plan_roles", None) else None
    option_supporter = (base_retriever.dense.option_support
                        if base_retriever is not None and args.option_support else None)
    identity = {"decoder": [decoder.name, decoder.version], "retrieval_mode": args.retrieval_mode, "k": args.k,
                "candidate_k": args.candidate_k, "reranker_batch_size": args.reranker_batch_size,
                "native_option_fusion": args.native_option_fusion,
                "retrieval_text_mode": args.retrieval_text_mode,
                "dense_index_dir": str(args.dense_index_dir) if args.dense_index_dir else None,
                "embedding_instruction_profile": args.embedding_instruction_profile,
                "embedding_instruction": embedding_instruction,
                "reranker_instruction_profile": args.reranker_instruction_profile,
                "reranker_instruction": reranker_instruction,
                "reranker_score_cache": args.reranker_score_cache,
                "option_support": args.option_support, "constrained_json": args.constrained_json,
                "plan_roles": list(plan_roles) if plan_roles else None,
                "prompt_version": getattr(decoder, "prompt_version", None), "citation_fill": args.citation_fill, "cite_mentions": args.cite_mentions, "doc_cap": args.doc_cap, "max_context": args.max_context, "fit_passages": args.fit_passages,
                "retriever": {"mode": args.retriever_mode, "rerank": args.rerank,
                              "graph_budget": args.graph_budget,
                              "exact_locator": args.exact_locator, "fixture_evidence": args.fixture_evidence,
                              "corpus_sha256": retriever.corpus_hash},
                "graph_policy": args.graph_policy, "plans": plans.manifest["experiment_id"] if plans else None}
    return Pipeline(retriever.retrieve, adapter=adapter, decoder=decoder, k=args.k, graph_policy=args.graph_policy,
                    retrieval_mode=args.retrieval_mode, plans=plans, max_refs=5 if args.citation_fill else 3,
                    citation_fill=args.citation_fill, cite_mentions=args.cite_mentions, native_option_fusion=args.native_option_fusion,
                    plan_roles=plan_roles, option_supporter=option_supporter, doc_cap=args.doc_cap), identity


def run_b_command(args, parser) -> int:
    from kingscode.reasoning.contracts import load_questions
    source = args.input or ROOT / "data/sample_50.jsonl"
    if args.command == "plan":
        from kingscode.reasoning.planner import PLANNER_PROMPT_VERSION, prompt_sha256
        items = _read_items(source, skip_options=args.retrieval_mode == "option_plan")
        if args.dry_run:
            print(json.dumps({"status": "prepared_not_executed", "questions": len(items), "model": args.model or "qwen3-8b",
                              "prompt_version": PLANNER_PROMPT_VERSION, "prompt_sha256": prompt_sha256()}, indent=2))
            return 0
        from kingscode.generation.planner_backend import QwenPlannerBackend
        from kingscode.reasoning.plan_store import freeze_plans
        out = freeze_plans(items, QwenPlannerBackend(args.model or "qwen3-8b", precision=args.precision))
        print(json.dumps({"plans": str(out), **json.loads((out / "manifest.json").read_text(encoding="utf-8"))["counts"]}, indent=2))
        return 0
    questions = load_questions(source)
    pipeline, identity = _pipeline(args)
    if args.command == "verify":
        from kingscode.reasoning.batch import verify_items
        if not args.delivered or not args.only:
            parser.error("verify needs --delivered and --only")
        report = verify_items(pipeline, questions, args.delivered, [int(x) for x in args.only.split(",")])
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return int(not report["all_match"])
    from kingscode.reasoning.batch import BatchRunner, synthetic_questions
    if not args.run_dir:
        parser.error("batch needs --run-dir")
    if args.synthetic:
        questions = synthetic_questions(questions, args.synthetic)
    report = BatchRunner(pipeline, args.run_dir, identity=identity, retries=args.retries,
                         show_answers=args.show_answers).run(questions, resume=not args.fresh)
    print(json.dumps({k: report[k] for k in ("submission", "rows", "complete", "fallback_ids", "submission_sha256", "counts", "seconds")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
