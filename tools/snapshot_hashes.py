"""Per-file SHA-256 manifest of the local corpus/index folders, and its verification.

    python tools/snapshot_hashes.py write  <out.json> corpus corpus_v01_v02_a1 ...
    python tools/snapshot_hashes.py verify <manifest.json>

`write` hashes every file under the given folders (relative paths, sorted) plus the git commit.
`verify` re-hashes the same paths in the current working directory and fails on any missing,
extra or changed file: tomorrow's corpus/index must be byte-identical to today's snapshot.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(folders: list[str]) -> dict[str, str]:
    files = {}
    for folder in folders:
        if Path(folder).is_file():
            files[Path(folder).as_posix()] = sha(Path(folder))
            continue
        for path in sorted(Path(folder).rglob("*")):
            if path.is_file():
                files[path.as_posix()] = sha(path)
    return files


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if argv[0] == "write":
        out, folders = Path(argv[1]), argv[2:]
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        files = collect(folders)
        out.write_text(json.dumps({"commit": commit, "folders": folders, "files": files}, indent=1) + "\n", encoding="utf-8")
        print(f"{len(files)} archivos con hash -> {out}")
        return 0
    manifest = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    now = collect(manifest["folders"])
    missing = sorted(set(manifest["files"]) - set(now))
    extra = sorted(set(now) - set(manifest["files"]))
    changed = sorted(p for p in set(now) & set(manifest["files"]) if now[p] != manifest["files"][p])
    print(json.dumps({"verificados": len(now), "faltan": missing[:10], "sobran": extra[:10], "cambiados": changed[:10],
                      "identico": not (missing or extra or changed), "commit_del_snapshot": manifest["commit"]}, indent=1))
    return 0 if not (missing or extra or changed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
