# Member A v0.2 progress — 2026-09-29

Status: PARTIAL. Branch `feat/member-a-corpus-v02-locator`, continuation parent `093265cdebf2233fc8dcc6bdc23aa120e68dc584`. Do not merge to `main`.

The completed G02, C01, P02 and P01 v0.2-only parser repairs, query-view/locator and retrieval-diagnostic work remain intact. Corpus v0.1 and the official starter pack remain untouched. Corpus v0.2 still contains four provisional documents, 72 passages, 33 nodes, 29 structural edges and zero active semantic edges. No corpus expansion or retrieval architecture change was justified by independent DEV evidence.

## 2026-09-29 — KC-COL-IR CUJ expansion and profile mapping

- Continued from parent `1beb08b0703af1f577d628d1826aecd2d2781f58` on `feat/member-a-corpus-v02-locator`. Preserved the already-dirty README and MASTER_KNOWLEDGE provenance changes and included them in the worktree review.
- Frozen the deterministic next 10 candidates before reading their text. Original 30 remain unchanged. The expansion item numbers are 22, 15, 39, 3, 26, 17, 21, 56, 5 and 25. Pool SHA-256: `af07237db321115562da4d64527c675d2bb99fe49c730b5f1ebcf2ac3bf85476`; selection SHA-256: `dc1332cb1477f96ea2652f2699befc317f4e053b67e8b8d987ef9397ecf13131`.
- Expansion dispositions: 1 accepted (Q025), 6 rejected for insufficient authoritative answer, 1 rejected as non-retrieval, 2 pending primary evidence (Q017 exact Auto 023; Q005 unnamed jurisprudence). Total reviewed candidates are 40; accepted total is 10. Gold IDs are Q009, Q012, Q013, Q025, Q030, Q031, Q037, Q043, Q045 and Q049.
- Built a controlled profile definition from all six textual PDFs in the full official CUJ 2026 ZIP; all 18 archive members were inventoried. Two MP3s were excluded without ASR. The deterministic in-memory extraction contains 191 physical pages / 190 nonempty passages, with passage hash `019dee8a805e87fbacfce45cd448f4b538b921d6d7c5aa7ff3a82a5472a894ef` and build hash `6bbf448a6cac3f368f0456699205f56891cbb144e4418a53c544d1753fb8f51b`. The passage file is not materialized in this worktree.
- Dual coverage is explicit: competitive corpus-v0.1 is MISSING for 10/10; controlled page mappings are COMPLETE for 10/10. Gold gate is unlocked; ranking execution stays locked by the current manifest until the controlled passage artifact is materialized; CUDA_READY=false.
- Added runner profile support and CPU integrity checks. `tools/verify_kc_col_ir_v01.py` passes; 11 focused unit tests pass; `independent_ir_v2.py check` reports the controlled corpus is not materialized. No retrieval, CUDA, encoder, reranker, decoder or validation performance was run/inspected.
- Next exact task: materialize the deterministic local/ignored corpus artifact, verify output file hashes against the frozen profile, then reconcile the ranking execution gate without changing question membership. Do not run C0-C3 or CUDA in this continuation.

## 2026-09-29 — Controlled CUJ profile materialized; stop before ranking

- Materialized the full frozen profile at `tmp/kc_col_ir_v0.1/controlled_cuj2026_v1/` from all six eligible textual PDFs in the hash-verified 18-member official archive. The profile includes 6 documents, 191 physical PDF pages and 190 nonempty passages; both MP3s remain excluded without ASR. Raw/derived files remain ignored and untracked.
- Passage file SHA-256 `c942cdfe6ec7f0c88ea0ebe4977540a99b93d98d3404b2972f9609b4499b3a7c`; runtime manifest SHA-256 `5bcb56f772c6f502d79c41cfef684e61e82b7cd13c7c3c442e35c73730974d3f`; BM25 SHA-256 `277184f3a954de79746589b1e28c932cd2d557bfc2a3e52fe9ab130d7e406a87`; corpus fingerprint `9569be4855bc9223eb346280de21d14b080da8e9b73aa9353175d59345492056`.
- Reconciled the prior extraction hash `019dee8a...`: it is the canonical passage JSONL hash with `member_index` omitted. The materialized schema adds that required member-provenance field; the new hash is calculated over the full serialized records and differs as expected.
- All 24 external-unit mappings (10 gold questions) point to 18 unique actual page passages with matching doc/member/page provenance. All controlled minimal evidence sets resolve. Competitive corpus-v0.1 remains 10/10 MISSING. GOLD_GATE and RANKING_GATE are unlocked; `ranking_n=10`, `retrieval_benchmark_ready=true`, `CUDA_READY=false` pending target-runtime handoff.
- CPU-only verification re-extracted the corpus for determinism, loaded BM25 and opened `Retriever` without issuing a query. No C0-C3, retrieval query, dense retrieval, reranking, CUDA or validation inspection ran.
- Next exact task: review the frozen handoff values on the target runtime, then conduct empirical ranking only in a separate authorized phase. Do not execute C0-C3 in this commit.

## Benchmark acquisition

Official ICFES indexing confirms the requested Gestión del Conflicto 2026 and Comunicación Jurídica 2021 question booklets. Direct original URLs, browser-compatible requests, the official toolbox landing navigation, and official current-module booklet candidates returned HTTP 404 in this runtime. This status is `RUNTIME_ACQUISITION_BLOCKED`; it does not establish that the official sources are unavailable. Search/index renderings were used only to discover official resources, never as question bytes.

The item sources are recorded in `benchmarks/kingscode_ir_v2/source_manifest.jsonl`: Gestión del Conflicto 2026 is DEV; Comunicación Jurídica 2021 and 2026 are separate VALIDATION candidates. The May 2026 Gestión URL is an official orientation guide, not a question booklet, and is not eligible for item intake. Current counts: independent items extracted 0; END_TO_END_ONLY 0; accepted RETRIEVAL_GOLD 0; NEEDS_HUMAN_REVIEW 0; sealed evaluation 0. No baseline is selectable.

A hash-gated local intake utility is ready. Place bytes in ignored `tmp/official-source-intake/` and run:
`python tools/benchmark_source_intake.py --source-id ICFES-GESTION-CONFLICTO-2026 --file tmp/official-source-intake/<file>.pdf --sha256 <64-hex-sha256>`
Use `ICFES-COMUNICACION-JURIDICA-2021` or `ICFES-COMUNICACION-JURIDICA-2026` for validation material. The May Gestión PDF is a guide, so it is excluded from question intake. The helper verifies the exact hash and PDF framing before reporting readiness; it does not claim source authenticity or redistribution rights. No questions are emitted or stored by the helper.

## Graph and identity review

G01 review rejected the seven known candidate edges whose target was the enclosing passage/section rather than the different legal provision named by the official text. Exact quote, official URL and SHA-256 of each containing source are recorded in `reports/member_a_v02/g01_relation_review_v02.json`. The seven replacement claims remain unresolved because the cited instruments' own primary bytes are not acquired. Active semantic edges remain zero; no graph expansion is enabled from this review.

D01 now has a regression asserting that equal content hashes do not collapse distinct canonical legal document IDs. The broader provenance and repeated-boilerplate audit remains open; the test does not mark D01 fixed.

## Verification and next action

Final verification: three complete passes overall; the latest pass includes the intake-source/guide correction and reports: 226 tests PASS; `python tools/benchmark_v2.py check` PASS (10 hashes; holdout not parsed; selection disabled); `python tools/verify_member_a_v02.py` PASS (19 official files, 326 v0.1 raw/clean files, 18 v0.2 hashes). The CPU snapshot check is not GPU metric replay. GPU, benchmark-v1, Search V2, target 4090 and holdout remain unrun. Do not tune before at least 10 accepted independent retrieval-gold items.

Next exact action: obtain the official PDFs and independent hashes, place them in `tmp/official-source-intake/`, verify with `tools/benchmark_source_intake.py`, then inspect current use terms and create exact, locally retained DEV/VALIDATION item records with source provenance. In parallel, acquire the seven G01 cited primary instruments before accepting any replacement edge.


## 2026-09-29 — KC-COL-IR-v0.1 cross-institution acquisition checkpoint

- Added the independent benchmark under `benchmarks/kc_col_ir_v0.1/`, separate from benchmark-v1 and the existing v2 technical pilot. The 17-row source inventory assigns Externado to DEV, Universidad Libre to VALIDATION_CANDIDATE, ICFES/SIRNA to SEALED_FUTURE, and guide-only sources to COVERAGE_ONLY.
- Acquired and SHA-256 verified two official Externado PDFs. The 2011 Externado Private I / Civil Procedure bank contains 270 distinct mechanically numbered candidate items. Its full text extraction and source PDFs are local under ignored `tmp/kc_col_ir_v0.1/`; question wording is not committed. Extraction has corrupted accent glyphs, so the candidate pool is frozen for QA only, not asserted as exact final transcription. The 2025 Labor PDF has 225 topic bullets and contributes zero independent items.
- Before any retrieval call, selected 30 of the 270 items in ascending SHA-256(`source_family + source_document + source_item_number`) order. All remain `NEEDS_HUMAN_REVIEW`, temporal status `UNCERTAIN`; zero accepted retrieval gold.
- Registered Universidad Libre's 2021 labor/public/private/penal URLs as isolated validation sources. Their HTTP responses were generic HTML, not PDFs; only signatures/status were checked. No validation text was extracted and no retrieval performance or gold was inspected. The 2026 thematic-bank announcement is coverage/methodology context, not 2021 question evidence.
- Added a dedicated runner with the C0 BM25, C1 Qwen dense, C2 hybrid/RRF, C3 hybrid/Qwen reranker configuration, identical depth and graph OFF; it hard-fails unless 10 accepted independent DEV golds are frozen. Runner has not been executed for retrieval. `CUDA_HANDOFF.md` is NOT READY (`CUDA_READY=false`): corpus/index hashes and current final SHA must be filled after the gate.
- Added `tools/verify_kc_col_ir_v01.py`; it verifies split-family isolation, inventory hashes, ignored pool hash, deterministic sampling, zero gold leakage and the closed baseline gate. Verification passes.
- G01: reject the seven wrong containing-passage targets; the seven replacement-effect claims remain unresolved/inactive. D01 content-dedup regression passes while the broader provenance audit remains open. G02/C01/P02/P01 remain fixed. Corpus v0.1 and Member B remain untouched.
- Next exact task: human-verify the 30 local source items/options against the original PDF and primary law, assign temporal status independently of retrieval, and accept at least 10 complete minimal-evidence packets before any baseline.


## 2026-09-29 — Cambio de prioridad DEV a fuentes recientes

- La cola primaria de `benchmarks/kc_col_ir_v0.1/questions/dev.jsonl` se reemplazó por 30 ítems deterministas del conjunto oficial JEP publicado en `/preguntas`. El HTML UTF-8 se preserva localmente con hash; pool completo de 62 y wording/respuestas permanecen ignorados fuera de Git. No se ha ejecutado retrieval ni seleccionado por rendimiento.
- Corrección de fecha: `/preguntas` corresponde a la tercera edición 2025; el sitio anuncia la cuarta edición 2026 pero no se verificaron preguntas 2026. La lista requiere filtro humano: hay aclaraciones fácticas, temas jurídicos/estratégicos y respuestas que remiten a expediente/jurisprudencia; algunas cuestiones jurídicas no reciben respuesta de fondo.
- Externado 2011 conserva intactos sus 30 IDs, regla de muestreo y 270 candidatos en archivos `reproducibilidad_externado_2011`; deja de ser DEV primario.
- Javeriana Seguros 2026 queda validation candidate. Se comprobó firma y SHA-256 de un PDF oficial de respuestas; no se extrajo texto ni se midió retrieval. La página indica que algunas respuestas deben inferirse del caso o son parte del análisis propio. Un segundo URL candidato respondió HTML y no se cuenta como PDF adquirido.
- Estado: 0 gold aceptados, 30 JEP por revisar, validación no parseada/no inspeccionada, `CUDA_READY=false`. Próximo paso: revisión humana de pregunta exacta, carácter implícito, evidencia mínima primaria y temporalidad para JEP; no correr baseline hasta >=10 gold válidos.


## 2026-09-29 — JEP candidate source review (no retrieval)

- Corrected the stale DEV/Externado/JEP family state: JEP 2025 is the frozen 30/62 DEV candidate batch; Externado 2011 stays reproducibility-only; Javeriana 2026 remains validation-only, unparsed and uninspected; JEP 2026 remains discovery-only.
- Independently reviewed all 30 exact frozen question/official-response pairs. Dispositions: 13 retrieval-gold candidates pending exact primary evidence, 5 explicit-reference/low-difficulty, 3 factual clarifications, 6 legal/strategy questions not answered, and 3 answers insufficient. No item was deleted or resampled; zero rejected; all 30 remain temporally unresolved.
- Acquired the official JEP Resolución de Conclusiones No. 02 de 2022 (3,142,097 bytes; SHA-256 `f098f08da604605108ffc2d84d60fd634ddcd44ef7ea5ba640591499972501d9`) and the official 2025 competition expediente ZIP (14,892,990 bytes; SHA-256 `f6d875129723a6d6ddfc27e32725cf6457846d692beff095e3d5729599e3ee8d`). All 22 archived PDFs have individual identity/hash/size/signature records in ignored acquisition metadata. Exact correspondence of these acquired materials to the sources and anonymized facts referenced by each sampled question remains unconfirmed; they are not silently substituted.
- No minimal evidence packets can yet be frozen, so accepted gold remains 0 and corpus coverage for accepted gold is N/A (0 COMPLETE/PARTIAL/MISSING/AMBIGUOUS; ranking denominator 0). KingsCode corpus v0.1 and `gold/dev.jsonl` remain unchanged. CUDA/baseline gate remains locked.
- Exact sources still needed: SRVR-012 resolution, relevant voluntary-version material, Auto SRVR-ADHC-023/2024, and any other source actually required item-by-item.


## 2026-09-29 — CUJ 2026 provenance correction and primary evidence pass

Source-page caveat: the current JEP `/preguntas` page is mixed-edition and retains stale “2025 / Tercera Edición” boilerplate. The 30 items are attributed to CUJ 2026 only because case identity and exact materials match the official 2026 packet; the 2025 SDSJ packet does not match. Original 30 sample IDs/item numbers and selection SHA are preserved; no resampling occurred.

- Corrected the current JEP source family/year from CUJ 2025 to CUJ 2026 without changing the deterministic sample: all 30 source item numbers and original selection SHA are preserved; IDs now include the legacy 2025 ID.
- Acquired the exact official CUJ 2026 ZIP (157,859,322 bytes; SHA-256 `3f9dc1765e8ea18588c13a48e1785b506f6a0c06eef3743057e2d34097d9b101`), verified 18 members/CRC and per-member hashes. It contains the hypothetical 147-page SRVR-012 resolution, Ainhoa and Laureano voluntary-version transcripts, two roadmap PDFs and audio. The Auto 023 document is referenced in the packet but is not a standalone member. The actual 2022 resolution and 2025 SDSJ ZIP remain explicitly excluded as substitutes.
- Reviewed all 30 exact frozen question/answer pairs against the current 2026 HTML and the primary packet. Dispositions: 9 accepted, 7 pending primary evidence, 8 rejected for insufficient authoritative answer, 6 rejected as non-retrieval. Q045/Q049 are preserved in duplicate group `EL_BILLAR_DATE`. Accepted set: Q009, Q012, Q013, Q030, Q031, Q037, Q043, Q045, Q049. Q031 is explicitly tagged low difficulty.
- External evidence units are separate from corpus passage IDs. A direct document-identity/full-text scan of corpus-v0.1’s 26,558 passages found no case-packet/source identity matches: 9 MISSING, 0 COMPLETE/PARTIAL/AMBIGUOUS; ranking_n=0.
- Runner now selects the intersection of frozen candidate IDs and accepted gold, has separate >=10 GOLD_GATE / >=10 COMPLETE RANKING_GATE, and scores only corpus passage IDs. CPU verifier and nine focused CPU tests were run; retrieval, CUDA, and validation parsing/performance inspection were not run. CUDA_READY=false.
- Next exact action: resolve at least one additional pending candidate from the primary packet or another exact official primary source without using retrieval outcomes; acquire standalone Auto 023 if Q043 requires it. Then update gold/corpus mappings and hashes. Keep ranking locked until ten golds have COMPLETE corpus evidence.


## 2026-09-30 — Pre-CUDA hardening continuation from main e528161

- Synchronized the clean local `main` to `origin/main` at `e52816145970adddc70300b1a9988c02b4cd1c8d` by fast-forward and created `exp/pre-cuda-hardening` from that commit. No source data or benchmark membership changed.
- Freeze commit `40590fc1a49e5d54a8398f255af5cdf1a47edc46` was pushed to `origin/exp/pre-cuda-hardening`; `main` remains unchanged at `e528161`.
- Added token-length audit tooling for the exact pinned Qwen encoder/reranker tokenizers. It reads only the frozen 10 DEV questions and 190 controlled passages, uses local snapshots only, and does not load model weights, query retrieval, or initialize CUDA. It was not run because the ignored controlled profile is absent in this checkout.
- Extended ranking reports with Candidate@30 metrics, candidate duplication diagnostics, execution identity, synchronous per-query timing, and correctly scoped initialization/total timings. Added a fail-closed invariant for duplicate or missing indexed `passage_id` values.
- Preregistered the maximum-two shortlist rule in `docs/experiments/KC_COL_IR_CUJ2026_SHORTLIST_V1.json`; Javeriana validation remains unparsed, so independent validation is not ready.
- `CUDA_READY=false`; no C0-C3, retrieval, CUDA, validation scoring, decoder, or tests were run in this continuation. Next exact action on the target machine: restore the frozen profile and pinned tokenizers, run `python tools/audit_kc_col_ir_tokens.py`, then complete the target-runtime handoff. The upstream handoff's stop-before-ranking instruction remains in force.
