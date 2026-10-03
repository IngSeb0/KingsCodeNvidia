"""Entregable 5: corpus_KingsCode.zip with the structure required by entregables/sabado/README.md.

    python tools/package_corpus_entrega.py                          # corpus_v01_v02_a1 -> dist/corpus_KingsCode.zip
    python tools/package_corpus_entrega.py --corpus corpus_v01_v02_a1 --write-root-manifest

corpus_KingsCode.zip
├── LICENSE                  CC BY 4.0 for our processing; the legal texts are public official sources
├── corpus_manifest.json     one record per document with doc_id, titulo, fuente, url, fecha_consulta, areas (+ trace)
├── corpus/<doc_id>.txt      cleaned text, one file per norm/decision (from every clean/ folder used)
└── indice/
    ├── chunks.jsonl         the indexed fragments (passage_id, doc_id, article, offsets, metadata, text)
    ├── bm25.json            lexical index actually used by the final retrieval
    ├── dense.npy + dense.meta.json   vector index (Qwen3-Embedding-0.6B), if built for this corpus
    └── graph/               normative graph (nodes/edges)

--write-root-manifest also writes the normalized manifest to ./corpus_manifest.json (entregable 4).
Reads only the local corpus; never touches the question files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
HOSTS = {"corteconstitucional.gov.co": "Relatoría de la Corte Constitucional",
         "cortesuprema.gov.co": "Corte Suprema de Justicia",
         "funcionpublica.gov.co": "Función Pública – Gestor Normativo",
         "normograma.sena.edu.co": "Normograma del SENA",
         "comunidadandina.org": "Comunidad Andina",
         "consejodeestado.gov.co": "Consejo de Estado",
         "secretariasenado.gov.co": "Secretaría del Senado",
         "suin-juriscol.gov.co": "SUIN-Juriscol"}
LICENSE = """Corpus KingsCode — Hackathon 2026 (Universidad de los Andes)

Los textos normativos y jurisprudenciales provienen de fuentes oficiales públicas de Colombia
(URL y fecha de consulta por documento en corpus_manifest.json). Los textos oficiales no están
sujetos a derechos de autor (Ley 23 de 1982, art. 41).

La limpieza, segmentación, metadatos, índices (léxico, vectorial y grafo normativo) y el
manifiesto producidos por el equipo KingsCode se publican bajo la licencia
Creative Commons Atribución 4.0 Internacional (CC BY 4.0):
https://creativecommons.org/licenses/by/4.0/
"""


def host_name(url: str) -> str:
    host = (url or "").split("/")[2].lower() if (url or "").count("/") >= 2 else ""
    host = host[4:] if host.startswith("www.") else host
    return HOSTS.get(host, host or "desconocida")


def normalize(doc: dict) -> dict:
    url = doc.get("url") or doc.get("source_url") or doc.get("requested_url")
    out = {"doc_id": doc["doc_id"],
           "titulo": doc.get("titulo") or doc.get("norm_name") or doc.get("source_title") or doc["doc_id"],
           "fuente": doc.get("fuente") or host_name(url),
           "url": url,
           "fecha_consulta": doc.get("fecha_consulta") or str(doc.get("retrieved_at") or "")[:10],
           "areas": doc.get("areas") or []}
    for k in ("norm_name", "source_type", "n_articulos", "n_fragmentos", "source_sha256", "sha256", "metodo_ingesta"):
        if doc.get(k) is not None:
            out[k] = doc[k]
    return out


def documents(corpus: Path) -> list[dict]:
    manifest = json.loads((corpus / "manifest.json").read_text(encoding="utf-8-sig"))
    docs = manifest.get("documentos") or manifest.get("documents") or []
    seen, out = set(), []
    for d in docs:
        if d.get("doc_id") and d["doc_id"] not in seen:
            seen.add(d["doc_id"])
            out.append(normalize(d))
    return out


def clean_texts(corpus: Path) -> dict[str, Path]:
    found = {}
    for folder in [corpus / "clean", ROOT / "corpus" / "clean", *sorted((ROOT / "corpora").glob("*/clean"))]:
        if folder.is_dir():
            for f in sorted(folder.glob("*.txt")):
                found.setdefault(f.stem, f)
    return found


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, default=ROOT / "corpus_v01_v02_a1")
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "corpus_KingsCode.zip")
    ap.add_argument("--write-root-manifest", action="store_true")
    args = ap.parse_args(argv)
    corpus = args.corpus if args.corpus.is_absolute() else ROOT / args.corpus
    if not (corpus / "manifest.json").exists():
        sys.exit(f"No existe {corpus}/manifest.json: construye o restaura el corpus primero.")
    docs = documents(corpus)
    texts = clean_texts(corpus)
    missing = [d["doc_id"] for d in docs if d["doc_id"] not in texts]
    manifest = {"equipo": "KingsCode", "licencia": "CC BY 4.0 (procesamiento); textos oficiales de dominio público",
                "n_documentos": len(docs), "documentos": docs}
    if args.write_root_manifest:
        (ROOT / "corpus_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    dense = (corpus / "index" / "dense.npy").exists()
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("LICENSE", LICENSE)
        z.writestr("corpus_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        for d in docs:
            if d["doc_id"] in texts:
                z.write(texts[d["doc_id"]], f"corpus/{d['doc_id']}.txt")
        z.write(corpus / "passages.jsonl", "indice/chunks.jsonl")
        for f in sorted((corpus / "index").glob("*")):
            if f.is_file():
                z.write(f, f"indice/{f.name}")
        for f in sorted((corpus / "graph").glob("*")) if (corpus / "graph").is_dir() else []:
            z.write(f, f"indice/graph/{f.name}")
    sha = hashlib.sha256(args.out.read_bytes()).hexdigest()
    print(json.dumps({"zip": str(args.out), "MB": round(args.out.stat().st_size / 2**20, 1), "sha256": sha,
                      "documentos": len(docs), "textos_incluidos": len(docs) - len(missing), "sin_texto": missing[:10],
                      "indice_vectorial": dense,
                      "aviso": None if dense else "Falta indice/dense.npy: construirlo con  .venv\\Scripts\\python.exe tools\\member_a.py dense --corpus "
                                                    + corpus.name + "  (GPU, ~5 min) y volver a empaquetar."},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
