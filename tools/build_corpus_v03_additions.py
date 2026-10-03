"""Build the pre-registered Council of State v0.3 source add-on reproducibly."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kingscode.common import ROOT, file_hash, read_json, write_json

PLAN_COMMIT = "3808846"
EXPECTED_DOCUMENTS = {
    "consejo_estado_suj_032_ce_s2_2023",
    "consejo_estado_unif_s3_24897_2012",
    "consejo_estado_suj_4_002_2022",
}


def build_additions(corpus: Path) -> dict:
    corpus = corpus.resolve()
    expected_dir = (ROOT / "corpora/corpus-v03-additions").resolve()
    if corpus != expected_dir:
        raise ValueError("Refusing to build outside the separate corpora/corpus-v03-additions directory")
    acquisition_path = corpus / "acquisition.json"
    acquisition = read_json(acquisition_path)
    if not acquisition.get("selection_pre_registered_before_download"):
        raise ValueError("The source selection plan must predate acquisition")
    if acquisition.get("selection_plan_commit") != PLAN_COMMIT:
        raise ValueError("Unexpected pre-registration commit")
    docs = acquisition.get("documents") or []
    if {d.get("doc_id") for d in docs} != EXPECTED_DOCUMENTS:
        raise ValueError("Acquired document IDs differ from the frozen three-source plan")
    for doc in docs:
        raw_path = (ROOT / doc["raw_path"]).resolve()
        if not raw_path.is_relative_to(corpus) or file_hash(raw_path) != doc["source_sha256"]:
            raise ValueError(f"Raw source is outside the add-on or has changed: {doc['doc_id']}")
        if doc.get("http_status") != 200 or doc.get("content_type") != "application/pdf":
            raise ValueError(f"Source response metadata is invalid: {doc['doc_id']}")

    from kingscode.corpus import build
    build(corpus)
    manifest_path = corpus / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("failures"):
        raise ValueError(f"Parser rejected source(s): {manifest['failures']}")
    parsed_docs = manifest.get("documentos") or []
    if {d.get("doc_id") for d in parsed_docs} != EXPECTED_DOCUMENTS:
        raise ValueError("Not all frozen documents were parsed")
    acquisition_by_id = {d["doc_id"]: d for d in docs}
    for doc in parsed_docs:
        source = acquisition_by_id[doc["doc_id"]]
        if doc.get("source_sha256") != source["source_sha256"]:
            raise ValueError(f"Parser output source hash mismatch: {doc['doc_id']}")
        # corpus.parse_document reports an extraction-method label as source_title;
        # preserve the publisher/document title separately and restore source_title.
        doc["document_title"] = source["source_title"]
        doc["parser_extraction_label"] = doc.get("source_title")
        doc["source_title"] = source["source_title"]
        doc["selection_plan_commit"] = PLAN_COMMIT
    manifest.update({
        "version": "corpus-v0.3-additions",
        "status": "provisional_additions_not_competitive_freeze",
        "selection_plan": "docs/CORPUS_V03_ACQUISITION_PLAN.md",
        "selection_plan_commit": PLAN_COMMIT,
        "selection_pre_registered_before_download": True,
        "acquisition_manifest_sha256": file_hash(acquisition_path),
        "bm25_sha256": file_hash(corpus / "index/bm25.json"),
        "policy": "Three pre-registered full-text official Council of State judgments; v0.1/v0.2 are unchanged; blank terminal pages are explicitly skipped and retained in raw PDFs; no blind questions or answer labels are read.",
    })
    write_json(manifest_path, manifest)
    return {
        "version": manifest["version"],
        "status": manifest["status"],
        "documents": manifest["n_documentos"],
        "passages": manifest["n_fragmentos"],
        "indexed_passages": manifest["n_indexed"],
        "nodes": manifest["n_nodes"],
        "edges": manifest["n_edges"],
        "hashes": {**manifest["hashes"], "index/bm25.json": manifest["bm25_sha256"]},
        "source_hashes": {d["doc_id"]: d["source_sha256"] for d in docs},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=ROOT / "corpora/corpus-v03-additions")
    args = parser.parse_args(argv)
    print(json.dumps(build_additions(args.corpus), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
