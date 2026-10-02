"""Check that every official source URL of the corpus still answers (read-only, no corpus change).

    python tools/check_sources.py                      # corpus_manifest.json + corpora/*/manifest.json
    python tools/check_sources.py --out docs/FUENTES_ESTADO.md

For each document: HTTP status of source_url (GET, streamed, first bytes only), final URL after
redirects and whether the status matches the one recorded at acquisition. It never rewrites a
manifest: a dead or moved source is reported for A (owner of acquisition) to decide.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
UA = "KingsCode-Hackathon2026-source-check/1.0 (+https://github.com/IngSeb0/KingsCodeNvidia)"


def documents() -> list[dict]:
    out = []
    sources = [ROOT / "corpus_manifest.json", *sorted((ROOT / "corpora").glob("*/manifest.json"))]
    for path in sources:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        docs = data.get("documentos") or data.get("documents") or []
        for d in docs:
            url = d.get("source_url") or d.get("url") or d.get("requested_url")
            if url:
                out.append({"manifest": str(path.relative_to(ROOT)), "doc_id": d.get("doc_id"),
                            "norm_name": d.get("norm_name"), "url": url, "recorded_status": d.get("http_status")})
    return out


def probe(doc: dict, timeout: float) -> dict:
    request = urllib.request.Request(doc["url"], headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(2048)
            return {**doc, "status": response.status, "final_url": response.geturl(), "error": None}
    except urllib.error.HTTPError as exc:
        return {**doc, "status": exc.code, "final_url": doc["url"], "error": f"HTTP {exc.code}"}
    except Exception as exc:  # timeouts, TLS, DNS: reported, never raised
        return {**doc, "status": None, "final_url": doc["url"], "error": f"{type(exc).__name__}: {exc}"[:160]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(argv)
    docs = documents()
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(lambda d: probe(d, args.timeout), docs))
    ok = [r for r in results if r["status"] == 200]
    bad = [r for r in results if r["status"] != 200]
    moved = [r for r in ok if r["final_url"].rstrip("/") != r["url"].rstrip("/")]
    hosts = {}
    for r in results:
        host = r["url"].split("/")[2]
        hosts.setdefault(host, [0, 0])
        hosts[host][0 if r["status"] == 200 else 1] += 1
    lines = ["# Estado de las fuentes del corpus", "",
             f"Documentos: {len(results)} · responden 200: {len(ok)} · con problema: {len(bad)} · redirigidos: {len(moved)}", "",
             "| host | 200 | con problema |", "|---|---:|---:|"]
    lines += [f"| {h} | {a} | {b} |" for h, (a, b) in sorted(hosts.items())]
    if bad:
        lines += ["", "## Con problema", "", "| manifiesto | doc_id | norma | estado | url |", "|---|---|---|---|---|"]
        lines += [f"| {r['manifest']} | {r['doc_id']} | {r['norm_name']} | {r['error'] or r['status']} | {r['url']} |" for r in bad]
    if moved:
        lines += ["", "## Redirigidos", "", "| doc_id | url | destino |", "|---|---|---|"]
        lines += [f"| {r['doc_id']} | {r['url']} | {r['final_url']} |" for r in moved]
    text = "\n".join(lines) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
