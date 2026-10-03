"""Une la entrega de las 992: base (final_p1 + final_p2) y, si se pide, reemplaza las filas de los
formatos re-corridos con busqueda semantica (mejora_p1..p3). Valida con el validador oficial.

  python tools/unir_entrega.py partir --partes 3 --formatos semi_open,open_ended
      -> data/test_992.mejora_parte{1,2,3}.jsonl (reparto round-robin, deterministico)
  python tools/unir_entrega.py unir --base A.jsonl B.jsonl [--mejora M1.jsonl M2.jsonl M3.jsonl
      --formatos semi_open,open_ended] --out submissions.jsonl

No edita respuestas: solo elige filas completas generadas por el pipeline (ninguna mezcla dentro de
una fila). Las filas reemplazadas vienen de una corrida completa y reproducible del mismo commit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))  # evaluate.py importa citations como modulo suelto
TEST = ROOT / "data/test_992.jsonl"


def read(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def partir(args):
    formats = set(args.formatos.split(","))
    rows = [r for r in read(TEST) if r["formato"] in formats]
    for k in range(args.partes):
        out = ROOT / f"data/test_992.mejora_parte{k + 1}.jsonl"
        part = rows[k::args.partes]
        out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in part), encoding="utf-8")
        print(f"{out.relative_to(ROOT)}: {len(part)} preguntas")


def unir(args):
    test = read(TEST)
    order = [r["id"] for r in test]
    fmt = {r["id"]: r["formato"] for r in test}
    rows = {}
    for path in args.base:
        for r in read(path):
            rows[r["id"]] = r
    missing = [i for i in order if i not in rows]
    if missing:
        sys.exit(f"STOP: a la base le faltan {len(missing)} ids (p.ej. {missing[:5]})")
    replaced = 0
    if args.mejora:
        formats = set(args.formatos.split(","))
        better = {}
        for path in args.mejora:
            for r in read(path):
                better[r["id"]] = r
        want = [i for i in order if fmt[i] in formats]
        lacking = [i for i in want if i not in better]
        if lacking and args.parcial:
            # Cada fila sigue siendo completa y de una sola configuracion reproducible; se registra
            # que ids vienen de la mejora para regenerarlos con su configuracion en la verificacion.
            print(f"AVISO: mejora parcial; {len(lacking)} ids de {sorted(formats)} se quedan con la base")
            want = [i for i in want if i in better]
        elif lacking:
            sys.exit(f"STOP: la mejora no cubre {len(lacking)} ids de {sorted(formats)} (p.ej. {lacking[:5]}); "
                     "esperar a que terminen las 3 partes o unir sin --mejora")
        for i in want:
            rows[i] = better[i]
            replaced += 1
    if args.mejora and args.ids_mejora:
        Path(args.ids_mejora).write_text("
".join(str(i) for i in want) + "
", encoding="utf-8")
    out = Path(args.out)
    out.write_text("".join(json.dumps(rows[i], ensure_ascii=False) + "\n" for i in order), encoding="utf-8")
    from scripts.evaluate import validate  # validador oficial (solo lectura)
    problems = validate([rows[i] for i in order], set(order))
    abst = sum(1 for i in order if rows[i].get("abstencion"))
    print(json.dumps({"archivo": str(out), "filas": len(order), "reemplazadas_con_mejora": replaced,
                      "abstenciones": abst, "problemas": problems if problems else 0,
                      "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}, ensure_ascii=False, indent=1))
    if problems:
        sys.exit(1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("partir")
    a.add_argument("--partes", type=int, default=3)
    a.add_argument("--formatos", default="semi_open,open_ended")
    b = sub.add_parser("unir")
    b.add_argument("--base", nargs="+", required=True)
    b.add_argument("--mejora", nargs="*", default=[])
    b.add_argument("--formatos", default="semi_open,open_ended")
    b.add_argument("--parcial", action="store_true",
                   help="reemplazar solo los ids que la mejora ya cubre (el resto se queda con la base)")
    b.add_argument("--ids-mejora", default="", help="archivo donde listar los ids tomados de la mejora")
    b.add_argument("--out", default=str(ROOT / "submissions.jsonl"))
    args = p.parse_args()
    partir(args) if args.cmd == "partir" else unir(args)


if __name__ == "__main__":
    main()
