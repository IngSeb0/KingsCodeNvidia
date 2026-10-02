"""Verify that a combined corpus still represents its two current inputs.

This is an integrity check, not retrieval or evaluation. It catches a stale
corpus_v01_v02 directory after either input has been replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kingscode.common import ROOT, file_hash, read_json


def _concatenated_hash(*paths: Path) -> str:
    digest = hashlib.sha256()
    for path in paths:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def verify(base: Path, addition: Path, combined: Path) -> dict:
    base, addition, combined = map(Path, (base, addition, combined))
    manifest = read_json(combined / "manifest.json")
    if manifest.get("status") != "diagnostic_not_competitive_freeze":
        raise ValueError("Unexpected combined-corpus status")
    inputs = list((manifest.get("inputs") or {}).values())
    expected_inputs = [
        {"version": read_json(path / "manifest.json").get("version"),
         "manifest_sha256": file_hash(path / "manifest.json"),
         "passages_sha256": file_hash(path / "passages.jsonl")}
        for path in (base, addition)
    ]
    if inputs != expected_inputs:
        raise ValueError("Combined corpus was built from different input manifests or passages")
    expected_passages = _concatenated_hash(base / "passages.jsonl", addition / "passages.jsonl")
    if file_hash(combined / "passages.jsonl") != expected_passages:
        raise ValueError("Combined passages are not the ordered concatenation of current inputs")
    for name, expected in (manifest.get("hashes") or {}).items():
        if file_hash(combined / name) != expected:
            raise ValueError(f"Combined output hash mismatch: {name}")
    if file_hash(combined / "index/bm25.json") != manifest.get("bm25_sha256"):
        raise ValueError("Combined BM25 hash mismatch")
    return {"status": "PASS", "base_passages_sha256": expected_inputs[0]["passages_sha256"],
            "addition_passages_sha256": expected_inputs[1]["passages_sha256"],
            "combined_passages_sha256": expected_passages,
            "bm25_sha256": manifest["bm25_sha256"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=ROOT / "corpus")
    parser.add_argument("--addition", type=Path, default=ROOT / "corpora/corpus-v0.2")
    parser.add_argument("--combined", type=Path, default=ROOT / "corpus_v01_v02")
    args = parser.parse_args()
    print(json.dumps(verify(args.base, args.addition, args.combined), indent=2))


if __name__ == "__main__":
    main()
