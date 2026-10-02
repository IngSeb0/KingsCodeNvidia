"""Render the one-page progress report (Markdown subset of the official template) to PDF.

    python tools/render_report_pdf.py docs/REPORTE_AVANCE_BORRADOR.md docs/entrega_viernes/REPORTE_AVANCE.pdf

Supports what the template uses: headings, bold, inline code, tables, numbered lists,
paragraphs and horizontal rules. Prints with headless Chrome/Edge and reports the page count
(the deliverable must be ONE page).
"""
from __future__ import annotations

import html
from pathlib import Path
import re
import shutil
import subprocess
import sys

CSS = """
@page { size: Letter; margin: 11mm 13mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 8.4pt; line-height: 1.28; color: #111; }
h1 { font-size: 13.5pt; margin: 0 0 3px; } h2 { font-size: 10pt; margin: 7px 0 3px; border-bottom: 1px solid #999; }
p { margin: 2px 0 4px; } hr { border: 0; border-top: 1px solid #bbb; margin: 4px 0; }
table { border-collapse: collapse; width: 100%; margin: 2px 0 4px; }
td, th { border: 1px solid #bbb; padding: 1.5px 4px; vertical-align: top; } th { background: #eee; text-align: left; }
td.n, th.n { text-align: right; white-space: nowrap; } ol { margin: 2px 0 2px 16px; padding: 0; } li { margin: 0 0 3px; }
code { font-family: Consolas, monospace; font-size: 7.8pt; } .meta p { margin: 0; }
"""


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)


def to_html(md: str) -> str:
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            align = ["n" if c.endswith(":") else "" for c in rows[1]] if len(rows) > 1 else []
            body = rows[2:] if len(rows) > 1 else rows[1:]
            cell = lambda tag, j, c: f'<{tag} class="{align[j] if j < len(align) else ""}">{inline(c)}</{tag}>'
            out.append("<table><tr>" + "".join(cell("th", j, c) for j, c in enumerate(rows[0])) + "</tr>"
                       + "".join("<tr>" + "".join(cell("td", j, c) for j, c in enumerate(r)) + "</tr>" for r in body) + "</table>")
            continue
        if re.match(r"\d+\. ", line):
            items = []
            while i < len(lines) and re.match(r"\d+\. ", lines[i]):
                items.append(re.sub(r"^\d+\. ", "", lines[i]))
                i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>")
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            out.append(f"<h{level}>{inline(line.lstrip('#').strip())}</h{level}>")
        elif line.strip() == "---":
            out.append("<hr>")
        else:
            out.append(f"<p>{inline(line)}</p>")
        i += 1
    return "\n".join(out)


def browser() -> str:
    for c in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              shutil.which("chrome") or "", shutil.which("msedge") or "", shutil.which("chromium") or ""):
        if c and Path(c).exists():
            return c
    sys.exit("No se encontró Chrome/Edge para imprimir el PDF.")


def main() -> int:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.parent.mkdir(parents=True, exist_ok=True)
    page = dst.with_suffix(".html")
    page.write_text(f"<!doctype html><html lang='es'><meta charset='utf-8'><title>Reporte de avance — KingsCode</title>"
                    f"<style>{CSS}</style><body>{to_html(src.read_text(encoding='utf-8'))}</body></html>", encoding="utf-8")
    subprocess.run([browser(), "--headless", "--disable-gpu", "--no-pdf-header-footer", "--print-to-pdf-no-header",
                    f"--print-to-pdf={dst.resolve()}", page.resolve().as_uri()], check=True, capture_output=True)
    pages = len(re.findall(rb"/Type\s*/Page[^s]", dst.read_bytes()))
    print(f"{dst} · páginas: {pages}")
    return 0 if pages == 1 else 2


if __name__ == "__main__":
    raise SystemExit(main())
