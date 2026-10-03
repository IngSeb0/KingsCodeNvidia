"""Split the blind test file into N contiguous parts (one per GPU), keeping lines byte-identical.

    python tools/split_test.py data/test_992.jsonl 2      # -> data/test_992.parte1.jsonl, data/test_992.parte2.jsonl

Each PC runs its part with the SAME commit and corpus; join the outputs with
`tools/validate_test_submission.py --test data/test_992.jsonl --merge <parte1> <parte2> --out submissions.jsonl`.
Live verification of an id is done on the PC that generated its part (ids per part are printed).
"""
from pathlib import Path
import json
import sys

src, n = Path(sys.argv[1]), int(sys.argv[2])
lines = [l for l in src.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
size = -(-len(lines) // n)
for k in range(n):
    part = lines[k * size:(k + 1) * size]
    out = src.with_name(f"{src.stem}.parte{k + 1}.jsonl")
    out.write_text("\n".join(part) + "\n", encoding="utf-8", newline="\n")
    ids = [json.loads(l)["id"] for l in part]
    print(f"{out}: {len(part)} preguntas, ids {ids[0]}..{ids[-1]}")
