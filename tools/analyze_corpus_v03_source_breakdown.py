"""Descriptive C0/C1 retrieval breakdown by area, evidence type, and authority.

Inputs are the independent Member-A benchmark run artifacts plus its DEV gold and
the v0.1 manifest. This tool never accepts or opens the blind 992 file.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

METRICS = (
    "Recall@1", "Recall@3", "Recall@5", "Recall@8", "Recall@10",
    "MRR@10", "nDCG@10", "Evidence Completeness@8",
    "Document Recall@1", "Document Recall@10", "Document Mismatch Rate",
    "unique_documents", "retrieved_characters",
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _run(path: Path) -> tuple[dict, dict[str, dict]]:
    if "test_992" in str(path).lower():
        raise ValueError("Blind 992 paths are forbidden")
    report = _read_json(path / "report.json")
    raw_rows = _read_jsonl(path / "per_question.jsonl")
    rows = {row["id"]: row for row in raw_rows}
    if report.get("status") != "passed" or len(rows) != len(raw_rows):
        raise ValueError(f"Invalid or duplicate run rows: {path}")
    return report, rows


def _source_classes(gold_docs: list[str], documents: dict[str, dict], field: str) -> str:
    values = set()
    for doc_id in gold_docs:
        doc = documents.get(doc_id) or documents.get(str(doc_id).split(":", 1)[0])
        if not doc:
            values.add("UNKNOWN")
            continue
        if field == "source_type":
            source_type = str(doc.get("source_type", "other")).lower()
            if source_type == "decision":
                values.add("jurisprudence")
            elif source_type in {"law", "decree", "code", "constitution"}:
                values.add("normative")
            else:
                values.add("other")
        else:
            values.add(str(doc.get("fuente") or "UNKNOWN"))
    if not values:
        return "UNKNOWN"
    return next(iter(values)) if len(values) == 1 else "MIXED"


def _aggregate(rows: list[dict]) -> dict:
    out = {key: mean(float(row["metrics"][key]) for row in rows) for key in METRICS}
    failures = Counter(row.get("failure", "unknown") for row in rows)
    out["questions"] = len(rows)
    out["failure_counts"] = dict(sorted(failures.items()))
    out["empty_retrievals"] = sum(not row.get("retrieved") for row in rows)
    out["latency_mean_ms"] = mean(float(row.get("latency_ms", 0)) for row in rows)
    return out


def _breakdown(c0: dict[str, dict], c1: dict[str, dict], labels: dict[str, dict[str, str]], dimension: str) -> dict:
    groups: dict[str, list[str]] = defaultdict(list)
    for question_id, metadata in labels.items():
        groups[metadata[dimension]].append(question_id)
    result = {}
    for label, ids in sorted(groups.items()):
        left = [c0[item] for item in ids]
        right = [c1[item] for item in ids]
        result[label] = {"questions": len(ids), "baseline": _aggregate(left), "candidate": _aggregate(right)}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run", required=True, type=Path)
    parser.add_argument("--candidate-run", required=True, type=Path)
    parser.add_argument("--corpus-manifest", required=True, type=Path)
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument("--paired-comparison", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-md", required=True, type=Path)
    args = parser.parse_args()
    for path in (args.baseline_run, args.candidate_run, args.corpus_manifest, args.gold, args.paired_comparison):
        if "test_992" in str(path).lower():
            raise ValueError("Blind 992 paths are forbidden")

    r0, c0 = _run(args.baseline_run)
    r1, c1 = _run(args.candidate_run)
    if (r0["git"] != r1["git"] or r0["variant"] != "R0" or r1["variant"] != "R0"
            or r0["split"] != "dev" or r1["split"] != "dev"
            or r0["benchmark"]["manifest_sha256"] != r1["benchmark"]["manifest_sha256"]
            or set(c0) != set(c1)):
        raise ValueError("Runs must be paired same-commit R0 DEV runs on the same benchmark")

    gold = {row["id"]: row for row in _read_jsonl(args.gold)}
    manifest = _read_json(args.corpus_manifest)
    documents = {doc["doc_id"]: doc for doc in manifest["documentos"]}
    labels: dict[str, dict[str, str]] = {}
    for question_id, row in c0.items():
        question = row["question"]
        gold_row = gold.get(question_id)
        if not gold_row:
            raise ValueError(f"Missing independent gold for benchmark id {question_id}")
        tags = set(question.get("tags", []))
        labels[question_id] = {
            "area": str(question.get("area", "UNKNOWN")),
            "reference_class": "explicit" if "EXPLICIT" in tags else "semantic_or_general",
            "source_type": _source_classes(gold_row.get("gold_document_ids", []), documents, "source_type"),
            "authority": _source_classes(gold_row.get("gold_document_ids", []), documents, "authority"),
        }

    breakdowns = {dimension: _breakdown(c0, c1, labels, dimension)
                  for dimension in ("area", "source_type", "authority", "reference_class")}
    explicit_counts = Counter(value["reference_class"] for value in labels.values())
    data = {
        "version": "corpus-v03-source-breakdown-v1",
        "status": "descriptive_breakdown; adoption_decision_uses_paired_gate",
        "git": r0["git"],
        "benchmark_manifest_sha256": r0["benchmark"]["manifest_sha256"],
        "baseline_corpus": r0["corpus"],
        "candidate_corpus": r1["corpus"],
        "question_count": len(c0),
        "explicit_vs_semantic_general_counts": dict(sorted(explicit_counts.items())),
        "source_type_mapping": {"decision": "jurisprudence", "law/decree/code/constitution": "normative"},
        "dimensions": breakdowns,
        "overall_paired_bootstrap": _read_json(args.paired_comparison)["bootstrap"],
        "limitations": [
            "The independent v1 benchmark has no semantic/general-reference questions; that subgroup is N=0.",
            "The DEV gold resolves only against v0.1 documents; the added Council of State sources have no gold cases here.",
            "Authority/source-type subgroup values are descriptive; the paired overall and area gate determines adoption.",
            "No blind 992 rows or labels are inputs to this report.",
        ],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Desglose Member-A C0/C1 por área, tipo de fuente y autoridad", "",
        f"- Rama/commit: `{r0['git']['branch']}` / `{r0['git']['commit']}`",
        f"- Benchmark DEV: `{data['benchmark_manifest_sha256']}`; n={len(c0)}; ambos R0/BM25.",
        "- Las métricas de subgrupo son descriptivas; la adopción usa la puerta pareada de 10.000 remuestras.",
        "- La muestra v1 no tiene preguntas semánticas/generales y no contiene gold para las nuevas fuentes del Consejo de Estado.",
        "",
    ]
    for dimension, groups in breakdowns.items():
        lines += [f"## {dimension}", "", "| Grupo | n | Recall@1 C0→C1 | Recall@5 | Recall@10 | MRR@10 | EC@8 | DocRecall@10 | Mismatch | Docs@10 | latencia media ms |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for group, values in groups.items():
            a, b = values["baseline"], values["candidate"]
            cells = [f"{a[key]:.3f}→{b[key]:.3f}" for key in ("Recall@1", "Recall@5", "Recall@10", "MRR@10", "Evidence Completeness@8", "Document Recall@10", "Document Mismatch Rate", "unique_documents", "latency_mean_ms")]
            lines.append(f"| {group} | {values['questions']} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["## Alcance", "", "- `explicit`: casos etiquetados EXPLICIT por el benchmark. No hay fila semántica/general porque el denominador es cero.", "- `normative` agrupa law/decree/code/constitution; `jurisprudence` agrupa decision. Casos con evidencia gold de más de una clase se etiquetan MIXED.", "- `authority` proviene de `fuente` del manifiesto del documento gold. El Consejo de Estado no aparece en estos estratos porque el v1 gold fue fijado sobre v0.1.", "- Ningún resultado de esta tabla habilita sample_50: revisar `reports/corpus_v03_independent_retrieval_comparison.json`.", ""]
    args.output_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"output_json": str(args.output_json), "output_md": str(args.output_md),
                      "questions": len(c0), "groups": {k: list(v) for k, v in breakdowns.items()}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
