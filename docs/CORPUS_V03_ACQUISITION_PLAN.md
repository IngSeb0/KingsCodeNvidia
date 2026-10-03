# Pre-registered corpus v0.3 acquisition plan

Date: 2026-10-03
Branch: `codex/corpus-first-final-improvement-20261003`
Baseline commit: `30ef38c792c33feb7dc6d87358ab749b007e8725` (`origin/main` at branch creation)

## Purpose and decision basis

The `corpus-v0.1` manifest contains no `decision` record from the Consejo de Estado (structured `fuente`/court/source metadata), while it already contains the principal general procedural instruments (including CPACA/Ley 1437, CGP/Ley 1564, and CPP/Ley 906). The first expansion therefore targets procedural jurisprudence and court diversity; it does not duplicate those codes. The selection is broad, source-driven, and fixed before downloading: three full-text unification judgments, one each from Sections II, III, and IV of the Council of State. No question, answer, output, or file from `data/test_992.jsonl` is an acquisition input.

The official unification catalogue describes Section II as public-service/labor/pension, Section III as including contracts and direct reparation, and Section IV as tax matters. Selecting one judgment from each is a small, reproducible authority-diversity sample, not a claim of complete coverage.

## Frozen source selection

1. **Section II — SUJ-032-CE-S2-2023**, rad. 66001-33-33-001-2022-00016-01 (5746-2022), 2023-10-11. Official full judgment: <https://www.consejodeestado.gov.co/wp-content/uploads/2023/113_660013333001202200016011SENTENCIA2023101119112_231012_124317%20%281%29.pdf>. The official Council publication identifies its unification rule as applying to public teachers and severance-pay delay; it adds an appellate interpretation addressing public employment, limitation periods and administrative claims.
2. **Section III — 24897**, rad. 73001-23-31-000-2000-03075-01, 2012-11-19. Official full judgment: <https://consejodeestado.gov.co/documentos/boletines/115/S3/73001-23-31-000-2000-03075-01%2824897%29.pdf>. It is listed in the Council's unification catalogue and addresses actio in rem verso / unjust enrichment and the appropriate contentious-administrative procedural route.
3. **Section IV — 2022CE-SUJ-4-002**, rad. 25000-23-37-000-2014-00507-01 (23854), 2022-09-08. Official full judgment: <https://consejodeestado.gov.co/wp-content/uploads/2022/UnifImp.pdf>. It unifies the procedure and time limits for correcting tax-return imputations under Article 43 of Law 962/2005.

These are not selected from the blind questions or from retrieval failures on those questions. No source is to be silently substituted. If the direct official source cannot be fetched, its identity cannot be validated in the document itself, or extraction materially fails, keep it unresolved and do not claim it was acquired.

## Acquisition and corpus rules

- Record the direct official URL, HTTP status, retrieval timestamp (UTC), content type, byte count, raw SHA-256, issuing court, decision identifier, date, title, parser version/status, clean-text SHA-256, and passage/index counts.
- Keep raw source files, clean text, and parsed passages under the separate `corpora/corpus-v03-additions/` directory. Never rewrite v0.1, v0.2, or `corpus-additions-v1`.
- Use the repository's existing PDF text extraction and decision segmentation. Check the header/radication/date and section boundaries against each source before indexing. Stop if the source is image-only, incomplete, unexpectedly unrelated, or fails the title/identifier checks; OCR/manual invention is out of scope.
- Set legal area and court from the source/document metadata, not from filenames. Preserve page provenance. Add only structural graph edges whose evidence is the source heading/passage; do not infer semantic relations or legal validity.
- Reject document-ID/canonical-body collisions and cross-source duplicate bodies during the deterministic combined build. No broad crawl and no second edition of the same decision.

## Evaluation and adoption

Build an ignored `corpus_v03_candidate` from the exact frozen v0.1 snapshot plus the already committed v0.2/additions-v1 sources and this add-on. Record exact artifact SHA-256 values and counts. Run the exact same BM25 implementation and parameters on the eligible DEV set of the independent Member-A benchmark only if its gold documents/passages map to the competitive corpus; report coverage and metric denominators before ranking. A benchmark profile whose gold is available only in a separate controlled packet is not a valid competitive-corpus comparison. If no like-for-like independent baseline/candidate mapping exists, report the gate as unavailable and do not claim improvement or adopt the candidate for a competitive freeze.

BM25 + option views + graph router + k=8 + prompt v6 remain the generation control. Do not rerun hybrid, v9, or a larger prompt. No GPU result is claimed by this CPU-only session. `sample_50` remains the only permitted end-to-end development selection gate.
