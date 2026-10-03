#!/usr/bin/env python3
"""Post-run audit of sample citation coverage; never used during retrieval/generation.

Compares sample legal-basis bodies with the emitted answer and attached evidence.
Classifies missed expected bodies as context-trimmed, absent from delivered evidence,
or available in evidence but omitted from the answer. It intentionally emits no
question/answer text and does not modify the submission.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import citations  # noqa: E402 - exact official citation extractor


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def _answer_text(row: dict) -> str:
    fmt = row.get("formato")
    fields = {
        "multiple_choice": ("justificacion",),
        "semi_open": ("respuesta", "referencia_legal"),
        "open_ended": ("marco_normativo", "analisis", "jurisprudencia", "conclusion"),
    }.get(fmt, ())
    return " ".join(str(row.get(field) or "") for field in fields)


def _bodies(text: str) -> set[tuple]:
    return citations.bodies(citations.extract(text or ""))


def classify(expected: set[tuple], supported: set[tuple], dropped: set[tuple],
             cited: set[tuple]) -> dict[str, set[tuple]]:
    """Split target bodies by the first pipeline stage that failed to preserve them."""
    return {
        "cited_and_supported": expected & supported & cited,
        "dropped_for_context": (expected - supported) & dropped,
        "missing_from_evidence": expected - supported - dropped,
        "available_but_not_cited": (expected & supported) - cited,
        "unsupported_citations": cited - supported,
        "extra_supported_citations": (cited & supported) - expected,
    }


def audit(run: Path, sample: Path) -> dict:
    batch = run if (run / "items").is_dir() else run / "batch"
    items_dir = batch / "items"
    if not items_dir.is_dir():
        raise FileNotFoundError(f"No existe items/: {items_dir}")

    labels = {int(row["id"]): row for row in _read_jsonl(sample)}
    details = []
    counts = {
        "expected_bodies": 0,
        "expected_bodies_supported_by_delivered_evidence": 0,
        "expected_bodies_cited_and_supported": 0,
        "expected_bodies_dropped_for_context": 0,
        "expected_bodies_missing_from_delivered_evidence": 0,
        "expected_bodies_available_but_not_cited": 0,
        "unsupported_cited_bodies": 0,
        "extra_supported_cited_bodies": 0,
    }

    for qid, label in sorted(labels.items()):
        expected = _bodies(label.get("legal_basis") or "")
        if not expected:
            continue
        item_path = items_dir / f"{qid}.json"
        if not item_path.is_file():
            details.append({"id": qid, "status": "missing_pipeline_output",
                            "missing_expected_bodies": [list(b) for b in sorted(expected, key=str)]})
            counts["expected_bodies"] += len(expected)
            counts["expected_bodies_missing_from_delivered_evidence"] += len(expected)
            continue

        item = json.loads(item_path.read_text(encoding="utf-8"))
        row = item.get("row") or {}
        trace = item.get("trace") or {}
        diagnostics = trace.get("diagnostics") or {}
        evidence = row.get("pasajes_recuperados") or []
        supported = set().union(*(_bodies(p.get("texto") or "") for p in evidence[:10])) if evidence else set()
        dropped = set()
        for entry in diagnostics.get("evidence_dropped_bodies") or []:
            for body in entry.get("bodies") or []:
                if isinstance(body, list) and len(body) == 3:
                    dropped.add(tuple(body))
        cited = _bodies(_answer_text(row))
        classes = classify(expected, supported, dropped, cited)
        miss_dropped = classes["dropped_for_context"]
        miss_evidence = classes["missing_from_evidence"]
        miss_citation = classes["available_but_not_cited"]
        counts["expected_bodies"] += len(expected)
        counts["expected_bodies_supported_by_delivered_evidence"] += len(expected & supported)
        counts["expected_bodies_cited_and_supported"] += len(classes["cited_and_supported"])
        counts["expected_bodies_dropped_for_context"] += len(miss_dropped)
        counts["expected_bodies_missing_from_delivered_evidence"] += len(miss_evidence)
        counts["expected_bodies_available_but_not_cited"] += len(miss_citation)
        counts["unsupported_cited_bodies"] += len(classes["unsupported_citations"])
        counts["extra_supported_cited_bodies"] += len(classes["extra_supported_citations"])

        if (miss_dropped or miss_evidence or miss_citation or classes["unsupported_citations"]
                or classes["extra_supported_citations"]):
            details.append({
                "id": qid,
                "status": "abstained" if row.get("abstencion") else "answered",
                "missing_expected_bodies_dropped_for_context": [list(b) for b in sorted(miss_dropped, key=str)],
                "missing_expected_bodies_absent_from_evidence": [list(b) for b in sorted(miss_evidence, key=str)],
                "expected_bodies_in_evidence_but_not_cited": [list(b) for b in sorted(miss_citation, key=str)],
                "unsupported_cited_bodies": [list(b) for b in sorted(classes["unsupported_citations"], key=str)],
                "extra_supported_cited_bodies": [list(b) for b in sorted(classes["extra_supported_citations"], key=str)],
                "retrieved_passage_count": len(evidence),
                "context_dropped_passage_ids": diagnostics.get("evidence_dropped_for_context") or [],
            })

    expected_n = counts["expected_bodies"]
    return {
        "run": str(batch),
        "sample": str(sample),
        "items_with_reference_citations": sum(bool(_bodies(row.get("legal_basis") or "")) for row in labels.values()),
        "metrics": {
            **counts,
            "evidence_coverage": round(counts["expected_bodies_supported_by_delivered_evidence"] / expected_n, 4) if expected_n else None,
            "supported_citation_recall": round(counts["expected_bodies_cited_and_supported"] / expected_n, 4) if expected_n else None,
        },
        "items_requiring_review": details,
        "scope": "Offline post-run body-level diagnosis using the same citation extractor as scripts/evaluate.py; it does not prove claim-level entailment.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="run folder or its batch/ folder")
    parser.add_argument("--sample", type=Path, default=ROOT / "data" / "sample_50.jsonl")
    parser.add_argument("--output", type=Path, help="optional JSON destination; stdout always gets the summary")
    args = parser.parse_args()
    report = audit(args.run, args.sample)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output) if args.output else None,
                      "metrics": report["metrics"],
                      "items_requiring_review": len(report["items_requiring_review"])},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
