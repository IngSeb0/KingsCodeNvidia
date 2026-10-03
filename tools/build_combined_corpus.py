"""Build a separate retrieval directory with corpus v0.1 + the provisional v0.2 additions.

    python tools/build_combined_corpus.py                      # corpus/ + corpora/corpus-v0.2 -> corpus_v01_v02/
    python tools/build_combined_corpus.py --base X --addition Y --out Z

Neither input is modified. Passages are concatenated (v0.1 first, then v0.2, each in
its own order); a doc_id or passage_id present in both inputs is an error, never a
silent override. Graph nodes/edges are concatenated; an identical node/edge present
in both is kept once, and a node_id with different content keeps the base (v0.1)
version and is counted in the manifest. BM25 is rebuilt over the combined indexable
passages with A's BM25Index. No dense index is built here.

v0.2 is `provisional_not_competitive_freeze`: the output is for diagnostics and
experiments until the team approves a v0.2 freeze in DECISION_LOG.md.
"""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kingscode.common import ROOT, file_hash, indexable, read_json, read_jsonl, write_json, write_jsonl
from kingscode.retrieval import BM25Index

FILES = ("passages.jsonl", "graph/nodes.jsonl", "graph/edges.jsonl", "index/bm25.json")


def _check_inputs(directory: Path, manifest: dict) -> None:
    for name in FILES:
        if not (directory / name).exists():
            raise FileNotFoundError(directory / name)
    expected_hashes = dict(manifest.get("hashes") or {})
    if manifest.get("bm25_sha256"):
        expected_hashes.setdefault("index/bm25.json", manifest["bm25_sha256"])
    for name, expected in expected_hashes.items():
        if (directory / name).exists() and file_hash(directory / name) != expected:
            raise ValueError(f"Input changed since its manifest: {directory / name}")


def _doc_ids(manifest: dict) -> set:
    return {d["doc_id"] for d in manifest.get("documentos") or manifest.get("documents") or []}


def combine(base: Path, addition, out: Path) -> dict:
    """addition: one directory or a list of directories, concatenated in order after base."""
    base = Path(base)
    additions = [Path(a) for a in (addition if isinstance(addition, (list, tuple)) else [addition])]
    out = Path(out)
    if out.resolve() in {base.resolve(), *(a.resolve() for a in additions)}:
        raise ValueError("Output must be a new directory; inputs are never modified")
    if (out / "manifest.json").exists():
        raise FileExistsError(f"{out} already holds a combined corpus; remove it explicitly to rebuild")
    base_manifest = read_json(base / "manifest.json")
    _check_inputs(base, base_manifest)
    inputs = [(base, base_manifest)]
    seen_docs = set(_doc_ids(base_manifest))
    for a in additions:
        m = read_json(a / "manifest.json")
        _check_inputs(a, m)
        overlap = seen_docs & _doc_ids(m)
        if overlap:
            raise ValueError(f"doc_id present in both corpora: {sorted(overlap)}")
        seen_docs |= _doc_ids(m)
        inputs.append((a, m))
    passages = [p for d, _ in inputs for p in read_jsonl(d / "passages.jsonl")]
    ids = [p["passage_id"] for p in passages]
    if len(ids) != len(set(ids)):
        raise ValueError("passage_id present in both corpora")
    nodes, conflicts = {}, 0
    for node in [n for d, _ in inputs for n in read_jsonl(d / "graph/nodes.jsonl")]:
        if node["node_id"] not in nodes:
            nodes[node["node_id"]] = node
        elif nodes[node["node_id"]] != node:
            conflicts += 1
    edges, seen = [], set()
    for edge in [e for d, _ in inputs for e in read_jsonl(d / "graph/edges.jsonl")]:
        key = json.dumps(edge, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            edges.append(edge)
    write_jsonl(out / "passages.jsonl", passages)
    write_jsonl(out / "graph/nodes.jsonl", sorted(nodes.values(), key=lambda n: n["node_id"]))
    write_jsonl(out / "graph/edges.jsonl", sorted(edges, key=lambda e: (e["source"], e["target"], e["relation"], e.get("evidence_passage_id") or "")))
    hashes = {name: file_hash(out / name) for name in FILES[:3]}
    index = BM25Index([p for p in passages if indexable(p)])
    index.save(out / "index/bm25.json", hashes["passages.jsonl"])
    root = ROOT.resolve()

    def display_path(directory: Path) -> str:
        resolved = directory.resolve()
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            return str(resolved)

    manifest = {
        "version": "corpus-v0.1+v0.2-initial-combined" + ("" if len(inputs) == 2 else f"+{len(inputs) - 2}-additions"),
        "status": "diagnostic_not_competitive_freeze",
        "inputs": {display_path(d):
                   {"version": m.get("version"), "manifest_sha256": file_hash(d / "manifest.json"),
                    "passages_sha256": file_hash(d / "passages.jsonl")}
                   for d, m in inputs},
        "n_documentos": len(seen_docs),
        "n_fragmentos": len(passages), "n_indexed": len(index.passages),
        "n_nodes": len(nodes), "n_edges": len(edges), "node_id_conflicts_kept_base": conflicts,
        "hashes": hashes, "bm25_sha256": file_hash(out / "index/bm25.json"),
        "documentos": [doc for _, m in inputs for doc in (m.get("documentos") or m.get("documents") or [])],
        "policy": "Concatenation only; no passage text, id or metadata is rewritten. Dense index not built.",
    }
    write_json(out / "manifest.json", manifest)
    return {k: v for k, v in manifest.items() if k != "documentos"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", type=Path, default=ROOT / "corpus")
    parser.add_argument("--addition", type=Path, action="append",
                        help="repeatable; default: corpora/corpus-v0.2 (+ corpora/corpus-additions-v1 if present)")
    parser.add_argument("--out", type=Path, default=ROOT / "corpus_v01_v02")
    args = parser.parse_args(argv)
    additions = args.addition or [ROOT / "corpora/corpus-v0.2"] + (
        [ROOT / "corpora/corpus-additions-v1"] if (ROOT / "corpora/corpus-additions-v1/manifest.json").exists() else [])
    print(json.dumps(combine(args.base, additions, args.out), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
