"""Coverage and provenance audit of a corpus manifest (never reads questions/answers)."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kingscode.common import ROOT, file_hash, indexable, read_json, read_jsonl, write_json

AREAS = ["constitutional", "administrative", "civil", "commercial_corporate", "family", "labor", "criminal", "procedural", "tax", "competition", "consumer", "data_protection", "intellectual_property"]
AUTHORITIES = ["Consejo de Estado", "Corte Constitucional", "Corte Suprema de Justicia", "Función Pública", "SENA", "Comunidad Andina"]
SOURCE_TYPES = ["constitution", "code", "decree", "decision", "law", "other"]
MARKET_AREA = "derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual]"
AREA_MAP = {
 "derecho constitucional": ["constitutional"], "derecho administrativo": ["administrative"],
 "derecho civil": ["civil"], "derecho comercial y sociedades": ["commercial_corporate"],
 "derecho de familia": ["family"], "derecho laboral": ["labor"], "derecho penal": ["criminal"],
 "derecho procesal": ["procedural"], "derecho tributario": ["tax"],
 MARKET_AREA: ["competition", "consumer", "data_protection", "intellectual_property"]}


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(c for c in value if not unicodedata.combining(c)).strip()


def _assert_not_blind_path(path: Path) -> None:
    """Reject direct blind-set inputs by path before any file is opened."""
    normalized = str(path).replace("\\", "/").casefold()
    if normalized.endswith("/data/test_992.jsonl") or path.name.casefold() == "test_992.jsonl":
        raise ValueError("Blind competitive file is forbidden as a corpus/report input")


def _areas(values) -> list[str]:
    out = []
    for value in values or []:
        key = _norm(value)
        mapped = AREA_MAP.get(key, [key or "(sin área declarada)"])
        for area in mapped:
            if area not in out:
                out.append(area)
    return out or ["(sin área declarada)"]


def _authority(doc: dict) -> str:
    raw = doc.get("court") or doc.get("institution") or doc.get("fuente") or doc.get("source_authority") or "(sin autoridad declarada)"
    key = _norm(raw)
    aliases = {
      "consejo de estado": "Consejo de Estado", "corte constitucional": "Corte Constitucional",
      "funcion publica": "Función Pública", "sena": "SENA", "comunidad andina": "Comunidad Andina"}
    if key.startswith("corte suprema de justicia"):
        return "Corte Suprema de Justicia"
    return aliases.get(key, str(raw).strip())


def _check_artifacts(corpus: Path, manifest: dict) -> dict:
    expected = dict(manifest.get("hashes") or {})
    bm25 = manifest.get("bm25_sha256") or expected.get("index/bm25.json")
    if bm25:
        expected.setdefault("index/bm25.json", bm25)
    actual = {}
    for rel, digest in expected.items():
        path = corpus / rel
        _assert_not_blind_path(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        got = file_hash(path)
        actual[rel] = got
        if got != digest:
            raise ValueError(f"Corpus hash mismatch for {rel}: expected {digest}, got {got}")
    return actual


def _artifact_set_hash(artifacts: dict[str, str]) -> str:
    """Path-independent identity for the exact runtime passage/graph/BM25 bytes."""
    payload = "".join(f"{name}\0{artifacts[name]}\n" for name in sorted(artifacts))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def analyze_corpus(corpus: Path, label: str | None = None) -> dict:
    corpus = Path(corpus)
    _assert_not_blind_path(corpus)
    manifest_path = corpus / "manifest.json"
    _assert_not_blind_path(manifest_path)
    manifest = read_json(manifest_path)
    artifact_hashes = _check_artifacts(corpus, manifest)
    documents = manifest.get("documentos") or manifest.get("documents") or []
    passages = read_jsonl(corpus / "passages.jsonl")
    nodes = read_jsonl(corpus / "graph/nodes.jsonl")
    edges = read_jsonl(corpus / "graph/edges.jsonl")
    doc_by_id = {d["doc_id"]: d for d in documents}
    passage_counts = Counter(p.get("doc_id") for p in passages)
    eligible_by_doc = Counter(p.get("doc_id") for p in passages if indexable(p))
    docs_by_area = Counter()
    eligible_by_area = Counter()
    totals_by_authority = Counter()
    decisions_by_authority = Counter()
    matrix_docs = Counter()
    matrix_passages = Counter()
    sources = []
    canonical_groups = defaultdict(list)
    manifest_failures = list(manifest.get("failures") or [])
    parser_failures = [f for f in manifest_failures if f.get("stage") in {"parse", "parser"}]
    acquisition_failures = [f for f in manifest_failures if f.get("stage") == "download"]
    incomplete_documents = []
    for d in documents:
        doc_id = d.get("doc_id", "")
        authority = _authority(d)
        source_type = d.get("source_type") or "(sin tipo)"
        doc_areas = _areas(d.get("areas"))
        totals_by_authority[authority] += 1
        if source_type == "decision":
            decisions_by_authority[authority] += 1
        canonical = d.get("canonical_body")
        if canonical:
            canonical_groups[json.dumps(canonical, ensure_ascii=False, sort_keys=True)].append(doc_id)
        if d.get("status") not in {None, "parsed", "parsed_provisional", "downloaded"}:
            incomplete_documents.append({"doc_id": doc_id, "status": d.get("status")})
        sources.append({"doc_id": doc_id, "title": d.get("document_title") or d.get("norm_name") or d.get("source_title"),
                        "court_or_authority": authority,
                        "authority_detail": d.get("court") or d.get("institution") or d.get("fuente") or d.get("source_authority"),
                        "source_type": source_type,
                        "areas": doc_areas, "retrieved_at": d.get("retrieved_at") or d.get("fecha_consulta"),
                        "source_url": d.get("source_url") or d.get("url"),
                        "http_status": d.get("http_status"), "bytes": d.get("bytes"),
                        "source_sha256": d.get("source_sha256"), "clean_sha256": d.get("sha256"),
                        "parser_version": d.get("metodo_ingesta") or d.get("parser_version") or manifest.get("parser_version"),
                        "parser_status": d.get("status"), "passages": passage_counts[doc_id],
                        "indexed_passages": eligible_by_doc[doc_id], "pdf_skip_pages": d.get("pdf_skip_pages", [])})
        for area in doc_areas:
            docs_by_area[(area, source_type)] += 1
            matrix_docs[(area, authority, source_type)] += 1
    for p in passages:
        doc = doc_by_id.get(p.get("doc_id"), {})
        authority = _authority(doc)
        source_type = p.get("source_type") or doc.get("source_type") or "(sin tipo)"
        passage_areas = _areas(p.get("areas") or doc.get("areas"))
        for area in passage_areas:
            if indexable(p):
                eligible_by_area[(area, source_type)] += 1
                matrix_passages[(area, authority, source_type)] += 1
    texts = defaultdict(list)
    for p in passages:
        text = unicodedata.normalize("NFC", (p.get("text") or "").strip())
        if text:
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            texts[digest].append(p.get("passage_id"))
    exact_duplicate_groups = {k: sorted(v) for k, v in texts.items() if len(v) > 1}
    cross_doc_groups = 0
    for ids in exact_duplicate_groups.values():
        if len({next((p.get("doc_id") for p in passages if p.get("passage_id") == pid), None) for pid in ids}) > 1:
            cross_doc_groups += 1
    canonical_collisions = {k: sorted(v) for k, v in canonical_groups.items() if len(v) > 1}
    authority_names = sorted(set(AUTHORITIES) | set(totals_by_authority))
    source_names = sorted(set(SOURCE_TYPES) | {k[1] for k in docs_by_area})
    matrix = []
    for area in AREAS:
        for authority in authority_names:
            for source_type in source_names:
                n_docs = matrix_docs[(area, authority, source_type)]
                n_passages = matrix_passages[(area, authority, source_type)]
                status = "empty" if n_docs == 0 else "sparse" if n_docs == 1 or n_passages < 50 else "limited" if n_docs < 3 or n_passages < 300 else "represented"
                matrix.append({"area": area, "authority": authority, "source_type": source_type,
                               "documents": n_docs, "indexed_passages": n_passages, "status": status})
    unresolved = {}
    backlog_path = ROOT / "reports/acquisition_backlog_v06.json"
    if backlog_path.exists():
        backlog = read_json(backlog_path)
        unresolved = {"total": backlog.get("total_unresolved"), "by_class": backlog.get("counts"),
                      "source_report": "reports/acquisition_backlog_v06.json"}
    graph_node_ids = {n.get("node_id") for n in nodes}
    passage_refs = {node_id for p in passages for node_id in (p.get("graph_node_ids") or [])}
    edge_refs = {e.get(key) for e in edges for key in ("source", "target")}
    evidence_ids = {p.get("passage_id") for p in passages}
    area_totals = {}
    for area in AREAS:
        area_totals[area] = {"documents": sum(v for (a, _), v in docs_by_area.items() if a == area),
                             "indexed_passages": sum(v for (a, _), v in eligible_by_area.items() if a == area)}
    docs_metadata_by_type = dict(sorted(Counter(d.get("source_type") or "(sin tipo)" for d in documents).items()))
    return {
      "label": label or corpus.name,
      "corpus_version": manifest.get("version"), "corpus_status": manifest.get("status"),
      "parser_version": manifest.get("parser_version"),
      "manifest_sha256": file_hash(manifest_path), "artifact_sha256": artifact_hashes,
      "artifact_set_sha256": _artifact_set_hash(artifact_hashes),
      "totals": {"documents": len(documents), "passages": len(passages),
                 "indexed_passages": sum(indexable(p) for p in passages),
                 "excluded_passages": sum(not indexable(p) for p in passages),
                 "graph_nodes": len(nodes), "graph_edges": len(edges)},
      "documents_by_area": {a: area_totals[a]["documents"] for a in AREAS},
      "indexed_passages_by_area": {a: area_totals[a]["indexed_passages"] for a in AREAS},
      "documents_by_authority": dict(sorted(totals_by_authority.items())),
      "decision_documents_by_authority": dict(sorted(decisions_by_authority.items())),
      "documents_by_source_type": docs_metadata_by_type,
      "coverage_matrix": matrix,
      "sparse_nonempty_cells": [c for c in matrix if c["status"] == "sparse"],
      "empty_cell_count": sum(c["status"] == "empty" for c in matrix),
      "source_inventory": sorted(sources, key=lambda r: r["doc_id"]),
      "canonical_body_collisions": canonical_collisions,
      "exact_duplicate_passage_text": {"groups": len(exact_duplicate_groups), "cross_document_groups": cross_doc_groups,
                                        "passages_in_groups": sum(map(len, exact_duplicate_groups.values()))},
      "parser_failures": parser_failures,
      "acquisition_failures": acquisition_failures,
      "incomplete_documents": incomplete_documents,
      "unresolved_acquisition_backlog": unresolved,
      "graph_integrity": {"passages_without_graph_nodes": sum(not (p.get("graph_node_ids") or []) for p in passages),
                           "dangling_passage_node_references": sum(node_id not in graph_node_ids for node_id in passage_refs),
                           "isolated_nodes": sum(node_id not in passage_refs and node_id not in edge_refs for node_id in graph_node_ids),
                           "edges_without_evidence_passage": sum(not e.get("evidence_passage_id") for e in edges),
                           "edges_with_unknown_evidence_passage": sum(bool(e.get("evidence_passage_id")) and e.get("evidence_passage_id") not in evidence_ids for e in edges)},
      "status_rules": {"empty": "0 documents in area × authority × source_type cell",
                       "sparse": "1 document or fewer than 50 indexed passages",
                       "limited": "fewer than 3 documents or fewer than 300 indexed passages",
                       "represented": "at least 3 documents and 300 indexed passages",
                       "note": "Inventory thresholds are diagnostic, not legal-quality certification."},
      "blind_set_policy": "This tool reads only the supplied corpus manifest, passages, graph, and acquisition-backlog report. It has no question/answer input and rejects data/test_992.jsonl as an input path.",
    }


def _markdown(report: dict, baseline: dict | None) -> str:
    lines = ["# Informe de cobertura del corpus", "",
             "Reporte de inventario y calidad de fuente; no usa etiquetas de respuesta ni archivos de preguntas.", "",
             "## Fingerprints y tamaños", "",
             "| Corpus | Versión | Documentos | Pasajes | Indexados | Excluidos | SHA manifest |", "|---|---|---:|---:|---:|---:|---|"]
    corpora = ([baseline] if baseline else []) + [report]
    for c in corpora:
        t = c["totals"]
        lines.append(f"| {c['label']} | {c['corpus_version']} | {t['documents']} | {t['passages']} | {t['indexed_passages']} | {t['excluded_passages']} | `{c['manifest_sha256']}` |")
    if baseline:
        old_ids = {r["doc_id"] for r in baseline["source_inventory"]}
        new_ids = {r["doc_id"] for r in report["source_inventory"]}
        lines += ["", f"Corpus candidato vs base: **+{len(new_ids-old_ids)} documentos**; **{report['totals']['indexed_passages']-baseline['totals']['indexed_passages']:+} pasajes indexables**."]
    lines += ["", "## Cobertura por área", "", "| Área | Documentos | Pasajes indexados |", "|---|---:|---:|"]
    for area in AREAS:
        lines.append(f"| {area} | {report['documents_by_area'][area]} | {report['indexed_passages_by_area'][area]} |")
    lines += ["", "## Autoridad y tipo de fuente", "", "| Autoridad | Total documentos | Decisiones |", "|---|---:|---:|"]
    for authority in sorted(report["documents_by_authority"]):
        lines.append(f"| {authority} | {report['documents_by_authority'][authority]} | {report['decision_documents_by_authority'].get(authority, 0)} |")
    lines += ["", "## Matriz no vacía: área × autoridad × tipo", "", "| Área | Autoridad | Tipo | Docs | Pasajes indexados | Estado |", "|---|---|---|---:|---:|---|"]
    for cell in report["coverage_matrix"]:
        if cell["documents"]:
            lines.append(f"| {cell['area']} | {cell['authority']} | {cell['source_type']} | {cell['documents']} | {cell['indexed_passages']} | {cell['status']} |")
    lines += ["", f"Celdas vacías en la matriz: **{report['empty_cell_count']}**. `sparse` significa una sola fuente o menos de 50 pasajes indexados; `limited` significa menos de tres fuentes o 300 pasajes. Son señales cuantitativas de inventario, no conclusiones sobre calidad jurídica.", "", "## Procedencia y controles", "",
              f"- Colisiones de cuerpo canónico: {len(report['canonical_body_collisions'])}.",
              f"- Grupos de texto de pasaje duplicado exacto: {report['exact_duplicate_passage_text']['groups']} ({report['exact_duplicate_passage_text']['cross_document_groups']} entre documentos).",
              f"- Fallas de parser registradas: {len(report['parser_failures'])}; adquisiciones fallidas: {len(report['acquisition_failures'])}; documentos incompletos/bloqueados: {len(report['incomplete_documents'])}.",
              f"- Referencias grafo→nodo faltantes: {report['graph_integrity']['dangling_passage_node_references']}.",
              f"- Nodos aislados: {report['graph_integrity']['isolated_nodes']}.",
              f"- Backlog de adquisición sin resolver: {report['unresolved_acquisition_backlog'].get('total', 'no reportado')}.",
              "- Los documentos mantienen URL, fecha de adquisición, SHA-256 de fuente, parser y conteos en `source_inventory` dentro del JSON.",
              "- No se leyó `data/test_992.jsonl`; el diagnóstico no admite preguntas ni respuestas.", "",
              "## Fuentes adquiridas en esta rama", "", "Ver [CORPUS_V03_ACQUISITION_PLAN.md](../docs/CORPUS_V03_ACQUISITION_PLAN.md) para criterios y URLs oficiales.", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True, help="Directory with manifest.json, passages.jsonl and graph/")
    parser.add_argument("--compare", type=Path, help="Optional baseline corpus directory")
    parser.add_argument("--output-json", type=Path, default=ROOT / "reports/corpus_coverage_final.json")
    parser.add_argument("--output-md", type=Path, default=ROOT / "reports/corpus_coverage_final.md")
    args = parser.parse_args(argv)
    _assert_not_blind_path(args.corpus)
    if args.compare:
        _assert_not_blind_path(args.compare)
    report = analyze_corpus(args.corpus)
    baseline = analyze_corpus(args.compare, label="corpus-v0.1 baseline") if args.compare else None
    report["comparison"] = None
    if baseline:
        old = {r["doc_id"] for r in baseline["source_inventory"]}
        new = {r["doc_id"] for r in report["source_inventory"]}
        report["comparison"] = {"baseline_label": baseline["label"], "baseline_totals": baseline["totals"],
                                "added_documents": sorted(new-old), "removed_documents": sorted(old-new),
                                "document_delta": len(new)-len(old),
                                "indexed_passage_delta": report["totals"]["indexed_passages"]-baseline["totals"]["indexed_passages"]}
    write_json(args.output_json, {"report": report, "baseline": baseline})
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(_markdown(report, baseline), encoding="utf-8", newline="\n")
    print(json.dumps({"json": str(args.output_json), "markdown": str(args.output_md),
                      "documents": report["totals"]["documents"], "indexed_passages": report["totals"]["indexed_passages"],
                      "empty_cells": report["empty_cell_count"], "comparison": report["comparison"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
