"""A's public retrieve -> B router -> policy -> backend -> guards -> schema."""
from __future__ import annotations

from copy import deepcopy
import inspect
from time import perf_counter

from .citation_builder import attach_references
from .citation_repair import count_citations, repair_citations
from .contracts import ANSWER_FIELDS, Question
from .decoder import GENERATION_CONFIG, Decoder, DummyDecoder, PromptSpec, abstention_row
from .guards import CitationGuardError, check_passages, citation_guard, validate_submission
from .policy import assess_evidence, blocking_reasons
from .query import NormalizedQuery, normalize_query
from .routing import RetrieverGraphRouter, route_graph


def query_variants(question: Question, query: NormalizedQuery) -> tuple[str, ...]:
    """One retrieval query per option for multiple_choice; the base query otherwise.

    Options carry terms the bare question omits (enunciado B.5's item 51: the
    action-type words needed to find Ley 472 de 1998 live in the options, not
    the question). Order is deterministic (sorted by letter) for reproducibility.
    """
    if question.format != "multiple_choice" or not question.options:
        return (query.retrieval_text,)
    return (query.retrieval_text,) + tuple(f"{query.retrieval_text} {v}" for _, v in sorted(question.options.items()))


def rrf_merge(ranked_lists: list[list[dict]], k: int, constant: int = 60) -> list[dict]:
    """Reciprocal rank fusion over A's own passage dicts; never mutates them."""
    scores: dict[str, float] = {}
    seen: dict[str, dict] = {}
    for ranked in ranked_lists:
        for rank, passage in enumerate(ranked):
            pid = passage["passage_id"]
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (constant + rank + 1)
            seen.setdefault(pid, passage)
    ordered = sorted(scores, key=lambda pid: (-scores[pid], pid))
    return [seen[pid] for pid in ordered[:k]]


RETRIEVAL_MODES = ("base", "option", "plan")
_LOCATOR_KWARGS = ("locator", "locator_injection", "exact_locator")
_PROFILE_SUM_FIELDS = (
    "dense_encoded_queries", "dense_encode_batches", "candidate_count", "reranker_pairs",
    "reranker_batches", "candidate_pairs_when_skipped", "bm25_ms", "dense_ms", "fusion_ms",
    "locator_ms", "graph_ms", "reranker_ms", "rerank_skip_recovery_ms", "total_ms",
)


def locator_switch(retrieve) -> str | None:
    """Name of A's per-call exact-locator switch, if retrieve() exposes one."""
    try:
        params = inspect.signature(retrieve).parameters
    except (TypeError, ValueError):
        return None
    return next((name for name in _LOCATOR_KWARGS if name in params), None)


def supports_query_views(retrieve) -> bool:
    """A's retrieve(question, k, graph_mode, query_views=...) (v0.2): locator on question only."""
    try:
        return "query_views" in inspect.signature(retrieve).parameters
    except (TypeError, ValueError):
        return False


def retrieval_views(question: Question, query: NormalizedQuery, mode: str, plan=None,
                   plan_roles: tuple[str, ...] | None = None) -> tuple[tuple[str, bool, str], ...]:
    """(text, trusted, role) per retrieval call. Q0 is always first and trusted.

    Options are organizer text (trusted). Planner views are model-generated:
    untrusted, so any statute/article they mention is plain retrieval text only.
    """
    q0 = (query.retrieval_text, True, "Q0")
    if mode == "base":
        return (q0,)
    if mode == "option":
        return (q0,) + tuple((v, True, "option") for v in query_variants(question, query)[1:])
    if mode == "plan":
        if plan is None:
            raise ValueError("plan mode needs a frozen plan (replay); plans are never generated inside the pipeline")
        allowed = set(plan_roles) if plan_roles else {"Q1", "Q2", "Q3"}
        selected = [(v, role) for v, role in zip(plan.views, plan.view_roles) if role in allowed]
        return (q0,) + tuple((v, False, role) for v, role in selected)
    raise ValueError(f"Unknown retrieval mode {mode}; plan+option is disabled until PLAN and OPTION are measured separately")


def _answer(question: Question, passages: list[dict], decoder: Decoder, *, max_refs: int = 3, citation_fill: bool = False,
            citation_fill_extra: int | None = None, cite_mentions: int = 0):
    check_passages(passages)
    evidence = deepcopy(passages[:10])
    assessment = assess_evidence(question.text, evidence)
    blocking = blocking_reasons(assessment, question.format)
    # Conflicting/ineligible text is never handed to the decoder or the guard,
    # whether or not it ends up blocking (e.g. it never blocks multiple_choice).
    if assessment.conflicts or "ineligible_evidence" in assessment.reasons:
        evidence = []
    # The official validator counts a non-abstaining row without pasajes_recuperados
    # as malformed (a failure, not even the 0.5), so no evidence => abstain, any format.
    if not evidence and not blocking:
        blocking = ("no_usable_evidence",)
    repair, refs, usage, before = None, [], {}, 0
    if blocking:
        reason, source = ",".join(blocking), "policy"
        row = abstention_row(question, evidence, reason)
    else:
        row = decoder.generate(question, deepcopy(evidence), PromptSpec(question.format), dict(GENERATION_CONFIG))
        usage = _usage(decoder)
        dummy = isinstance(decoder, DummyDecoder)
        reason = "dummy_backend_no_legal_reasoning" if dummy else None
        source = "dummy_backend" if dummy else "decoder"
        if isinstance(row, dict) and row.get("abstencion") is False and row.get("id") == question.id \
                and row.get("formato") == question.format:
            # Decoder reasons; citations are repaired against the evidence, then
            # final citation strings come from the deterministic builder (B2/B3).
            source, before = "none", count_citations(row)
            row, repair = repair_citations(row, evidence)
            row, refs = attach_references(row, evidence, usage.get("attribution"), max_refs, fill_ranked=citation_fill,
                                          fill_ranked_limit=citation_fill_extra, mentions=cite_mentions)
            if question.format != "multiple_choice" and any(
                    row.get(k) in (None, "", [], {}) for k in ANSWER_FIELDS[question.format]):
                reason, source = "citation_repair_emptied_required_field", "citation_repair"
                row = abstention_row(question, evidence, reason)
    if not isinstance(row, dict) or row.get("id") != question.id or row.get("formato") != question.format:
        raise ValueError("Decoder changed question identity/format or did not return an object")
    guard = citation_guard(row, evidence, allow_body_mentions=bool(cite_mentions))
    validate_submission(row)
    attribution = usage.get("attribution") or {"status": "legacy_fallback" if not blocking else "not_applicable", "ids": []}
    return row, {"assessment": assessment.record(), "warnings": [r for r in assessment.reasons if r not in blocking],
                 "abstention_reason": reason if row["abstencion"] else None, "abstention_source": source if row["abstencion"] else "none",
                 "citation_guard": guard, "citation_repair": repair, "built_references": refs,
                 "diagnostics": generation_diagnostics(decoder, usage, attribution, before, guard, repair, evidence, row)}


def _usage(decoder) -> dict:
    """Decoder-reported usage (HFDecoder.last_usage); anything that is not a dict is ignored."""
    usage = getattr(decoder, "last_usage", None)
    return dict(usage) if isinstance(usage, dict) else {}


def generation_diagnostics(decoder, usage, attribution, before, guard, repair, evidence, row) -> dict:
    """Label-free per-question generation diagnostics (no gold, no thresholds)."""
    actions = {}
    for action in (repair or {}).get("actions", []):
        actions[action["action"]] = actions.get(action["action"], 0) + 1
    return {"decoder": getattr(decoder, "name", type(decoder).__name__), "decoder_version": getattr(decoder, "version", None),
            "model": usage.get("model"), "revision": usage.get("revision"),
            "prompt_version": usage.get("prompt_version", PromptSpec(row["formato"]).version), "prompt_sha256": usage.get("prompt_sha256"),
            "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
            "generation_ms": usage.get("generation_ms"), "peak_vram_bytes": usage.get("peak_vram_bytes"),
            "peak_reserved_vram_bytes": usage.get("peak_reserved_vram_bytes"),
            "normalization_action": usage.get("normalization_action"), "decoder_abstained": usage.get("decoder_abstained"),
            # Exact decoder text before citation repair/builder, for offline review only: it never
            # enters the official row, and presentation.view_model never shows it.
            "raw_response": usage.get("raw_response"),
            "attribution_status": attribution.get("status"), "attribution_count": len(attribution.get("ids", [])),
            "attribution_reason": attribution.get("reason"), "format_warnings": list(usage.get("format_warnings") or []),
            "field_coercions": list(usage.get("field_coercions") or []), "evidence_in_prompt": usage.get("evidence_in_prompt"),
            "constrained_json": usage.get("constrained_json", False),
            "json_grammar": usage.get("json_grammar"),
            "json_grammar_sha256": usage.get("json_grammar_sha256"),
            "xgrammar_version": usage.get("xgrammar_version"),
            "evidence_dropped_for_context": list(usage.get("evidence_dropped_for_context") or []),
            "citations_before_repair": before, "citations_after_repair": guard["citation_count"],
            "repair_actions": actions, "evidence_passages": len(evidence),
            "evidence_ids_delivered": [p.get("passage_id") for p in row["pasajes_recuperados"]],
            "evidence_ids_used": list(attribution.get("ids", []))}


def answer(question: Question | str, passages: list[dict], format: str, *, question_id: int = 0, decoder: Decoder | None = None) -> dict:
    """Question carries the official ID; ad-hoc strings use question_id (default 0)."""
    q = Question(question_id, question, format) if isinstance(question, str) else question
    if not isinstance(q, Question) or q.format != format:
        raise TypeError("Use Question/plain text with a matching format; never a raw labeled row")
    return _answer(q, passages, decoder or DummyDecoder())[0]


class Pipeline:
    def __init__(self, retrieve, *, adapter: RetrieverGraphRouter | None = None, decoder: Decoder | None = None,
                 k: int = 8, graph_policy: str = "router", retrieval_mode: str = "option", plans=None,
                 max_refs: int = 3, citation_fill: bool = False, citation_fill_extra: int | None = None,
                 cite_mentions: int = 0, native_option_fusion: bool = False,
                 plan_roles: tuple[str, ...] | None = None, option_supporter=None):
        if type(k) is not int or not 1 <= k <= 10 or graph_policy not in {"router", "off", "auto", "on"}:
            raise ValueError("Invalid evidence count/graph policy")
        if retrieval_mode not in RETRIEVAL_MODES:
            raise ValueError(f"retrieval_mode must be one of {RETRIEVAL_MODES}; plan+option stays disabled until measured")
        if retrieval_mode == "plan" and plans is None:
            raise ValueError("plan mode replays frozen plans: pass plans=PlanStore(...)")
        if type(native_option_fusion) is not bool:
            raise ValueError("native_option_fusion must be a boolean")
        if plan_roles is not None and (not plan_roles or set(plan_roles) - {"Q1", "Q2", "Q3"}):
            raise ValueError("plan_roles must be a nonempty subset of Q1/Q2/Q3")
        self.retrieve, self.adapter = retrieve, adapter
        self.decoder, self.k, self.graph_policy = decoder or DummyDecoder(), k, graph_policy
        self.retrieval_mode, self.plans, self.max_refs = retrieval_mode, plans, max_refs
        self.citation_fill = citation_fill
        if citation_fill_extra is not None and (type(citation_fill_extra) is not int or citation_fill_extra < 0):
            raise ValueError("citation_fill_extra must be a nonnegative integer")
        self.citation_fill_extra = citation_fill_extra
        self.cite_mentions = cite_mentions
        self.native_option_fusion = native_option_fusion
        self.plan_roles, self.option_supporter = plan_roles, option_supporter
        self.locator_kwarg = locator_switch(retrieve)
        self.native_views = supports_query_views(retrieve)

    def _call(self, text: str, trusted: bool, mode: str) -> list[dict]:
        if not trusted and self.locator_kwarg:
            return self.retrieve(text, self.k, mode, **{self.locator_kwarg: False})
        return self.retrieve(text, self.k, mode)

    def _fetch(self, views, mode: str) -> list[dict]:
        return self._fetch_with_profiles(views, mode)[0]

    @staticmethod
    def _profiles_from(passages: list[dict]) -> list[dict]:
        if not passages:
            return []
        profile = (passages[0].get("retrieval") or {}).get("profile")
        return [profile] if isinstance(profile, dict) else []

    @staticmethod
    def _aggregate_view_profiles(profiles: list[dict]) -> list[dict]:
        """Return one per-pass profile, summing work across sequential fan-out calls.

        A's profile is repeated on every returned passage. Capture only the first
        copy per retrieve() call; aggregate calls without touching passage objects
        or their ranking/evidence metadata. Native fusion and single-view calls
        retain the original profile values.
        """
        if not profiles:
            return []
        if len(profiles) == 1:
            return [dict(profiles[0])]

        result = dict(profiles[0])
        for field in _PROFILE_SUM_FIELDS:
            values = [p.get(field) for p in profiles]
            numeric = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
            if numeric:
                total = sum(numeric)
                result[field] = round(total, 3) if field.endswith("_ms") else int(total)

        view_counts = [p.get("query_view_count", 1) for p in profiles]
        numeric_view_counts = [v for v in view_counts if isinstance(v, int) and not isinstance(v, bool)]
        if numeric_view_counts:
            result["query_view_count"] = sum(numeric_view_counts)

        statuses = {p.get("reranker_status") for p in profiles}
        if any(status is not None for status in statuses):
            result["reranker_status"] = next(iter(statuses)) if len(statuses) == 1 else "mixed"
        return [result]

    def _fetch_with_profiles(self, views, mode: str) -> tuple[list[dict], list[dict]]:
        # One view (the common case) keeps the exact call A/tests expect. Several
        # views (options or planner) fan out through A's public retrieve() and
        # are fused deterministically with RRF.
        if len(views) == 1:
            passages = self._call(views[0][0], views[0][1], mode)
            return passages, self._aggregate_view_profiles(self._profiles_from(passages))
        if self._native(views):
            # A's own multi-view path: the exact locator, graph router and
            # reranker see only Q0; generated views only widen candidates.
            passages = self.retrieve(views[0][0], self.k, mode, query_views=[text for text, _, _ in views[1:]])
            return passages, self._aggregate_view_profiles(self._profiles_from(passages))
        ranked_lists = []
        profiles = []
        for text, trusted, _ in views:
            ranked = self._call(text, trusted, mode)
            ranked_lists.append(ranked)
            profiles.extend(self._profiles_from(ranked))
        return rrf_merge(ranked_lists, self.k), self._aggregate_view_profiles(profiles)

    def _native(self, views) -> bool:
        if len(views) < 2 or not self.native_views or not views[0][1]:
            return False
        if all(not trusted for _, trusted, _ in views[1:]):
            return True
        return (self.native_option_fusion and self.retrieval_mode == "option"
                and all(trusted and role == "option" for _, trusted, role in views[1:]))

    def _locator_control(self, views) -> str | None:
        if self._native(views):
            return "a_query_views_locator_on_q0_only"
        if all(trusted for _, trusted, _ in views):
            return None
        return "disabled_for_generated_views" if self.locator_kwarg else "retrieve_has_no_locator_switch"

    def run(self, question: Question):
        if not isinstance(question, Question):
            raise TypeError("Pipeline only accepts a public Question")
        start = perf_counter()
        query = normalize_query(question.text)
        plan = self.plans.get(question.id, question.text) if self.retrieval_mode == "plan" else None
        variants = retrieval_views(question, query, self.retrieval_mode, plan, self.plan_roles)
        flat, flat_profiles = self._fetch_with_profiles(variants, "off")
        check_passages(flat)
        decision = route_graph(query, flat) if self.graph_policy == "router" else self.graph_policy
        executed = "off"
        passages = flat
        passage_profiles = flat_profiles
        if decision != "off":
            if self.adapter:
                self.adapter.bind(query.retrieval_text, decision)
            # Without a bound callback, call A explicitly with ON instead of
            # silently falling back to A's question-only provisional AUTO router.
            executed = decision if decision == "on" or self.adapter else "on"
            passages, passage_profiles = self._fetch_with_profiles(variants, executed)
        option_support = None
        if self.option_supporter and question.format == "multiple_choice" and passages:
            option_support = self.option_supporter(question.text, question.options, passages)
            for passage in passages:
                passage["option_support"] = {letter: round(float(scores.get(passage["passage_id"], 0.0)), 6)
                                              for letter, scores in option_support.items()}
        retrieved_ms = (perf_counter() - start) * 1000
        retrieval_profiles = flat_profiles + (passage_profiles if executed != "off" else [])
        try:
            row, trace = _answer(question, passages, self.decoder, max_refs=self.max_refs, citation_fill=self.citation_fill,
                                 citation_fill_extra=self.citation_fill_extra,
                                 cite_mentions=getattr(self, "cite_mentions", 0))
        except CitationGuardError as exc:
            # Enunciado B.5: an unsupported/unsafe citation must be corrected or
            # suppressed, never void the whole run. _answer/answer() still raise
            # for direct callers (e.g. tamper-detection tests); only the batch
            # pipeline downgrades this single item to abstention so the other
            # 991 questions still publish. See docs/DECISION_LOG.md.
            evidence = deepcopy(passages[:10])
            row = abstention_row(question, evidence, "citation_guard_rejected")
            guard = citation_guard(row, evidence)
            usage = _usage(self.decoder)
            trace = {"assessment": None, "abstention_reason": "citation_guard_rejected", "abstention_source": "citation_guard_fallback",
                     "diagnostics": generation_diagnostics(self.decoder, usage, usage.get("attribution") or {"status": "legacy_fallback", "ids": []},
                                                           0, guard, None, evidence, row),
                     "citation_guard": guard, "citation_guard_fallback": exc.report}
        trace.update(retrieval_mode=self.retrieval_mode,
                     views=[{"role": role, "trusted": trusted, "text": text} for text, trusted, role in variants],
                     locator_control=self._locator_control(variants),
                     native_option_fusion=bool(self.native_option_fusion and self.retrieval_mode == "option"
                                               and len(variants) > 1 and self._native(variants)),
                     plan_roles=list(self.plan_roles or ("Q1", "Q2", "Q3")),
                     option_support_enabled=option_support is not None,
                     option_support_ms=getattr(getattr(self.option_supporter, "__self__", None),
                                               "last_option_support_ms", None),
                     option_support=option_support,
                     retrieval_profiles=retrieval_profiles,
                     plan=None if plan is None else {"status": plan.status,
                                                     "generated_references": [list(map(str, r)) for r in plan.generated_references]})
        trace.update(id=question.id, query=query.record(), graph_decision=decision, graph_execution=executed,
                     flat_passage_ids=[p["passage_id"] for p in flat], final_passage_ids=[p["passage_id"] for p in passages],
                     latency_ms=(perf_counter() - start) * 1000, retrieval_ms=retrieved_ms,
                     rerank_skipped=any((p.get("retrieval") or {}).get("rerank_skipped") for p in passages))
        return row, trace
