# KingsCode internal retrieval benchmark methodology v1

## Purpose and data boundary

This benchmark measures evidence retrieval against the frozen official-corpus snapshot, not answer generation. It is independent from the official 50-question sample. Inputs and gold labels are stored separately. The runner first retrieves using only `id`, `question`, `area`, `format`, and `tags`; it loads gold only after rankings are complete. `expected_answer`, `respuesta_correcta`, `texto_respuesta_correcta`, and official `legal_basis` are forbidden from benchmark retrieval inputs and corpus/index artifacts.

All populated v1 questions are deterministic templates over verified document/article/section metadata and source spans. No closed model, agent-generated legal question, synthetic answer, or fabricated semantic paraphrase is used. A candidate needing semantic/temporal wording goes to `authoring/review_queue.jsonl` with `needs_human_question_text=true`.

## Splits and tuning protocol

V1 final is stratified by declared legal area: 120 dev, 40 validation, 40 holdout. The initial **100-case checkpoint** is explicitly 60/20/20 and is only a schema/evaluator/data-quality gate; it cannot select a production retrieval configuration. Development supports implementation/debugging; validation supports selecting a configuration only after final V1 is built. Holdout is protected: the evaluator rejects it unless a predeclared purpose is supplied (`predeclared_baseline` for R0 or `post_selection_confirmation` after a recorded selection). The official 50 is never development data for this benchmark; it is an external confirmation after internal selection.

## Gold definitions

A gold document is a `canonical_document_id`; a gold fragment is a `canonical_fragment_id`. Direct evidence is required to satisfy the legal locator/source-derived question. A generated multi-evidence case has two distinct direct gold fragments. Spans are exact `[clean_start, clean_end)` intervals of a gold passage.

## Metrics

All rank metrics use deterministic `passage_id` tie handling and evaluate the first `k` returned passages.

- **Recall@k / Passage Recall@k**: macro mean over cases of `|gold_fragment_ids ∩ retrieved_fragment_ids[:k]| / |gold_fragment_ids|`.
- **Document Recall@10**: macro mean over cases of the analogous fraction of gold document IDs recovered in the first ten passages.
- **MRR@10**: reciprocal of the rank of the first passage whose canonical fragment ID is direct gold; zero if absent through rank ten.
- **MAP@10**: mean average precision at ten, where each direct gold fragment can contribute once. Average precision is divided by the number of direct gold fragments.
- **nDCG@10**: mean DCG/ideal DCG at ten; direct evidence has gain 1 and supporting evidence gain 0.5. Repeated retrieval of a gold fragment gives no additional gain.
- **Evidence Completeness@8/@10**: fraction of cases for which *all* direct gold fragment IDs occur by k. This is the primary decision metric at 8 because B receives eight passages.
- **Document Mismatch Rate**: fraction of cases whose rank-1 canonical document is not a gold document. This is a project definition; it is not claimed to equal any named academic DRM metric.
- **Span Recall / Span Precision**: when spans are present, a retrieved passage matches a gold span if its clean-text interval overlaps it and canonical fragment IDs match. Recall is matched gold spans / gold spans; precision is retrieved spans overlapping a gold span / retrieved passages with offsets.
- **Context cost**: mean returned passage count, character count, deterministic tokenizer-token count, unique canonical documents, and duplicate canonical fragment count.
- **Latency**: p50 and p95 in milliseconds measured around retrieval only; model initialization is recorded separately.

Metrics are reported overall and by legal area, behavior tag, explicit-vs-semantic, and single-vs-multi-evidence.

## Variants and isolation

R0 is BM25/OFF. R1-BGE and R1-QWEN are dense-only with identical corpus/question/chunking/k/gold. R2 variants add RRF at existing `candidate_k=30` and RRF constant 60. R3 adds only the Qwen reranker to the selected R2. R4/R5 compare only graph AUTO/ON against R3/OFF. R6/R7/R8 are the existing metadata/structure ablations on the selected R3. No blocked variant is assigned results. CPU BM25 diagnostics are labelled diagnostics and never presented as an R3-based ablation.

## Complementarity and statistics

For same-ID runs, complementarity at k records `both_hit`, `bm25_only`, `dense_only`, and `both_miss`, then intersection, union, and oracle-union recall. Dense is not rejected solely for lower aggregate recall if it has material dense-only recovery.

Paired bootstrap uses the same question IDs, seed 0, 10,000 resamples, and percentile 95% confidence intervals for a candidate-minus-baseline delta. Minimum target comparisons are Evidence Completeness@8, Recall@10, and MRR@10. An interval spanning zero is reported as inconclusive, not decisive.

## Failure loop

Failures are classified as `corpus_missing`, `wrong_document`, `correct_document_wrong_passage`, `ranking_failure`, `graph_failure`, or `ambiguous_gold`. The action maps respectively to acquisition/coverage, canonical/document retrieval, locator/chunking, ranker, graph traversal, or annotation QA. Corpus expansion is evidence-driven; no failure authorizes blind expansion.

## Reproducibility and review

Every run stores git branch/commit, corpus/graph/BM25 hashes, model and config identity, benchmark manifest hash, split, seed, hardware/runtime, latency, aggregate/subgroup metrics, and per-question outcomes. The final critic pass verifies schema, gold/input separation, split disjointness, corpus gold resolution, absence of closed-model content, holdout/official-50 discipline, metric tests, reproducibility, unchanged official files, and unchanged Member B code.

### Append-only corpus comparison C0/C1

For a corpus-only experiment, run R0 BM25/OFF on `corpus-v0.1` and on an
append-only candidate, with the same source commit and DEV question/gold split.
`--allow-corpus-additions` verifies the pinned baseline artifacts, candidate
provenance, and byte-identical baseline passage prefix; it refuses validation
for neural variants, holdout, or a changed baseline. `analyze_retrieval_benchmark.py
compare --allow-corpus-change` then requires same-commit R0 runs and paired IDs.
Use `tools/gate_corpus_expansion.py` for paired bootstrap checks on Evidence
Completeness@8, Recall@10, and MRR@10 overall and by administrative, procedural,
and tax area. This measures whether expansion perturbs retrieval for the fixed
independent benchmark; it does not create evidence questions for newly added
authorities. A corpus addition still needs independently accepted coverage for
its own authority before a competitive freeze. No holdout or blind-set content
is used in C0/C1.


## KC-COL-IR-v0.1 independent gold and corpus coverage

Gold relevance is established from independent external primary evidence, not from the contents or outputs of the KingsCode retrieval system. Gold acceptance requires an exact source question, a legitimate retrieval target, independently verified primary evidence, temporal review, and a frozen minimal evidence set. The presence of those sources in the frozen KingsCode corpus is not an acceptance requirement. Each accepted gold item receives a separate corpus coverage label: COMPLETE, PARTIAL, MISSING, or AMBIGUOUS.

Absence of required gold evidence from the frozen corpus is reported as corpus_missing and is not converted into a retrieval ranking failure. PARTIAL and MISSING coverage are excluded from pure ranking metric denominators; PARTIAL is reported as corpus_missing until a complete minimum evidence set is represented. AMBIGUOUS coverage is reported separately and excluded from ranking metrics.

Retriever-ranking metrics are reported on the subset for which the frozen corpus contains sufficient gold evidence, while corpus coverage metrics are reported across all accepted gold. Every metric reports its denominator: ranking metrics use COMPLETE coverage only; missing/partial/complete/ambiguous rates use all accepted gold. If no gold has been accepted, both populations have n=0 and rates are N/A. Gold evidence provenance and acquired primary source bytes are kept separate from the competitive corpus; source acquisition does not authorize corpus modification.
