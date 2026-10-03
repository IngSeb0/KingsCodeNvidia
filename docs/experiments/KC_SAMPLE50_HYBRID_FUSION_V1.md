# Sample 50: hybrid + reranker optimization experiment

Status: preregistered diagnostic plan; no GPU result is implied by this document.

## Follow-up candidate on the current recommended B profile (2026-10-03)

`-Recomendada` currently uses B's `option` orchestration and A's BM25 backend; it does not load A's dense encoder. The following two catalog entries keep the recommended prompt/citation settings, hybrid retrieval, reranker, graph router, candidate depth and exact reranker-score cache constant. They differ only in how the trusted multiple-choice options reach A:

- `hybrid_recommended_fanout_cache`: legacy B fan-out, one call to A per option.
- `hybrid_recommended_native_cache`: A's `query_views` fusion, one call per graph pass.

The exact locator stays off in this pair because the legacy path would apply it to each option while A's native path intentionally applies it only to Q0. Compare both candidates with a separate `-Recomendada` run on the same corpus snapshot. This is a runtime/quality experiment, not a change to the default or proof that native fusion improves score. Native fusion changes ranking semantics.

On the RTX 4090, after confirming no other user/process occupies the GPU, run:

```powershell
$Repo = "$HOME\KingsCodeGPU\KingsCodeNvidia"
Set-Location $Repo

# Use the same corpus/model snapshot as the baseline run. If its score is not
# 37.46, pass the measured same-snapshot score to -Base for the comparison table.
powershell -ExecutionPolicy Bypass -File .\tools\kingscode_variantes.ps1 `
  -Work $Repo `
  -Variantes hybrid_recommended_fanout_cache,hybrid_recommended_native_cache `
  -Base 37.46
```

For each run compare `evaluation_official.json`, `batch_report.json` and `RESUMEN.json`: official total and per-format points; `reranker_computed_pairs`, cache hits, `reranker_ms`, `dense_ms`, graph-pass count, generation and retrieval percentiles, peak VRAM and seconds/question. Then run the official baseline and candidate comparison to completion before choosing a winner. Run RAGAS only once on a selected complete run; this pair does not invoke it.

## What this tests

The current `option` path makes one retrieval call for Q0 and another for each multiple-choice option. With hybrid retrieval and reranking, each call builds its own candidate pool and reranks it. The opt-in `--native-option-fusion` path sends Q0 plus all trusted option text to A's existing `query_views` interface. A encodes uncached dense query views in configured batches, fuses their sparse/dense rankings, and applies the reranker once to the fused pool using Q0. This changes ranking semantics, so the default remains the existing fan-out path until the paired GPU run is reviewed.

The new profile records BM25, dense, fusion, exact locator, graph and reranker time; candidate and reranker-pair counts; dense query encodes/batches; reranker mini-batches; and total time. The batch report also summarizes citation support from the deterministic guard, abstentions by format/reason, retrieval-stage percentiles and total reranker work. These diagnostics are label-free. A supported citation is evidence of citation-grounding under the guard's syntactic criterion, not proof that the cited passage semantically entails every sentence.

## Fixed conditions

Use the same 4090 PC, repository commit, Python environment, Qwen revisions, input file, corpus path and corpus hashes for paired runs. Keep Qwen3-8B, BF16, temperature zero, prompt v3, `k=8`, graph router, exact-locator off, citation fill off, and RAGAS off for the retrieval-speed comparison. The controlled hyperparameters are option-view fusion (legacy fan-out vs native), exact reranker-score cache (off vs on), candidate depth (30 vs 15), and reranker GPU forward batch size (2 vs 1). Cache reuse is exact for identical model revision, instruction, query and passage text; the LRU is capped at 8,192 pairs. Do not change these together when interpreting a pair. The combined v0.1+v0.2 corpus remains diagnostic only; a changed live source snapshot is not a competitive corpus freeze.

Record `RESUMEN.json`, `batch_report.json`, `evaluation_official.json`, each run's `identity.json`, and the corpus manifest/hashes. Compare official score and format metrics alongside latency; do not select a faster setting that reduces answer quality without an explicit team decision.

## Paired run sequence

First use a balanced pilot of 12 public questions (4 per format) to screen five profiles. Generate the pilot JSONL from the public question fields only; do not copy answer keys, expected answers, or legal bases into the model input. The pilot is for runtime, VRAM, valid output, citation/abstention diagnostics only; do not choose a quality winner from its small labeled subset. Run every profile on the same pilot IDs:

1. Legacy fan-out, candidate depth 30, reranker batch 2, score cache off.
2. Native option fusion, candidate depth 30, reranker batch 2, score cache off.
3. Native option fusion, candidate depth 30, reranker batch 2, score cache on.
4. Native option fusion, candidate depth 15, reranker batch 2, score cache off.
5. Native option fusion, candidate depth 30, reranker batch 1, score cache off.

Then run the full 50-question sample for the baseline and the chosen comparison profile(s), with the official evaluator and live replay. Run RAGAS only once, on one explicitly selected full-sample configuration, because it spends OpenRouter credits.

The direct PowerShell commands are provided in the execution handoff in chat; no matrix `.ps1` is required. A single full-sample pair can also be run directly as follows:

```powershell
$Repo = "$HOME\KingsCodeGPU\KingsCodeNvidia"
Set-Location $Repo

& .\tools\kingscode_pc_nueva_diagnostico.ps1 `
  -Work $Repo -CorpusSet "v01+v02" -AllowKnownLocalCorpusDrift `
  -Model "qwen3-8b" -RunName "hybrid_c30_legacy" `
  -RetrieverMode hybrid -Rerank -CandidateK 30 -RerankerBatchSize 2 -SkipSmoke

& .\tools\kingscode_pc_nueva_diagnostico.ps1 `
  -Work $Repo -CorpusSet "v01+v02" -AllowKnownLocalCorpusDrift `
  -Model "qwen3-8b" -RunName "hybrid_c30_native_option_fusion" `
  -RetrieverMode hybrid -Rerank -CandidateK 30 -RerankerBatchSize 2 -NativeOptionFusion -SkipSmoke

& .\tools\kingscode_pc_nueva_diagnostico.ps1 `
  -Work $Repo -CorpusSet "v01+v02" -AllowKnownLocalCorpusDrift `
  -Model "qwen3-8b" -RunName "hybrid_c30_native_option_fusion_cache" `
  -RetrieverMode hybrid -Rerank -CandidateK 30 -RerankerBatchSize 2 `
  -NativeOptionFusion -RerankerScoreCache -SkipSmoke
```

The output prints progress and estimated remaining time per question. For a long run, inspect `reports/decoder_diagnostic/<RunName>/batch/items/*.json` and `batch/batch_report.json`; don't start a second process against the same run directory. The live verifier replays three items and is included by default.

For the other full-sample hyperparameter comparisons, keep native fusion enabled and change only one value: add `-RerankerScoreCache` (off to on), use `-CandidateK 15` (from 30), or use `-RerankerBatchSize 1` (from 2). The score cache's first graph-off pass may have no hits; graph-on reuse should report hits in `batch_report.json`. After retrieval is selected, test prompt v4 and citation fill independently, keeping the chosen retrieval setting fixed. Do not combine prompt v4 and citation fill in the same comparison.

## Citations, abstention, and corpus

- Keep the citation guard and hard abstention policy unchanged during the first retrieval comparison. It blocks empty/ineligible/conflicting evidence for free text, while multiple choice always attempts an answer under the stated score rule. Do not tune lexical-overlap or abstention thresholds to the 50 labeled items.
- `-CitationFill` is an optional citation-recall experiment for semi-open and multiple-choice outputs only. Every filled citation is built from a retrieved passage and checked by the existing guard. Compare supported/unsupported citation counts and the official citation score. It does not certify semantic entailment.
- `-PromptVersion v4` separately tests explicit abstention/schema/length instructions. Compare abstention reasons, fallbacks, valid rows, official score and citation support. Keep v3 as the default until reviewed.
- Do not edit corpus v0.1 or promote the four provisional v0.2 documents based on sample scores. Improve corpus coverage only from official primary sources with preserved final URL, source identity, bytes, SHA-256 and human review. Keep every acquired or rebuilt corpus separately versioned, and rebuild its indexes from those exact passage bytes.
- RAGAS is intentionally excluded from the paired latency/score runs. It uses reserved OpenRouter credits and remains paused until the team's existing authorization is given.

## Current interpretation of the slow run

The earlier two-hour estimate is not enough to identify the bottleneck. The attached `-ExactLocator` BM25 run was at `2bc419d0e383f3d4865b1b2670853e6caae87e43`, before main's `40ca511` SDPA/reranker hardening, so it does not measure the current code. Compare `generation_ms_p50/p95` with `retrieval_stage_ms.reranker_ms`, `dense_ms`, `reranker_pairs`, VRAM peak and progress timestamps. If generation dominates, retrieval fusion cannot explain the whole delay; if reranking dominates and native fusion cuts pairs while preserving score, it is the appropriate speed/quality trade-off to consider. The SDPA change from main still needs a same-machine sample run; the 4090 smoke alone does not establish 50-question throughput.

## Background references

- Hugging Face documents SDPA as a supported attention backend selected through Transformers' attention interface: [Attention backends](https://huggingface.co/docs/transformers/main/attention_interface).
- PyTorch's scaled-dot-product attention API can dispatch to optimized kernels subject to input constraints: [scaled_dot_product_attention](https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.scaled_dot_product_attention.html).
- Qwen's official model cards describe the Qwen3 embedding and reranking models used here: [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B/blob/main/README.md), [Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B/blob/main/README.md).
