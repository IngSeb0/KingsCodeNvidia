"""Version-isolated source repairs for corpus-v0.2.

Corpus-v0.1 continues to call ``corpus.parse_document`` without overrides. This
module sanitizes only verified source structure before invoking the shared
extractor and records source units for stable v0.2 fragment identity.
"""
from __future__ import annotations

import re
from html import escape

from .common import indexable
from .corpus import HEADING, SourceBlock, blocks_from_html, blocks_from_pdf, parse_document

PAGINATED_TOC_ROW = re.compile(r"\s+\d{1,3}\s*$")
STANDALONE_ARTICLE = re.compile(r"^art[ií]culo\s+\d+(?:\s*[.,]\s*\d+)*(?:[a-z])?$", re.I)
PUBLISHER_REPEAL = re.compile(
    r"^\s*(?:<[^>]{1,120}>\s*[.]?\s*)?(?:[<(]\s*)?"
    r"(?:art[ií]culo\s+)?derogad[oa]\s+por\b", re.I)


def remove_decision_table_of_contents(blocks: list[str]) -> tuple[list[str], list[dict]]:
    """Remove a publisher-marked index run, retaining the surrounding source.

    A block named ÍNDICE/TABLA DE CONTENIDO starts the run. Only following
    blocks that end in a printed page number are removed; the first non-page
    heading ends the run and remains in the document.
    """
    result, exclusions = [], []
    in_toc = False
    for index, block in enumerate(blocks):
        flat = " ".join(str(block).split()).strip()
        if not in_toc and re.fullmatch(r"(?:[IVX]+[. ]+)?(?:ÍNDICE|TABLA DE CONTENIDO|TABLA DE CONTENIDOS)", flat, re.I):
            in_toc = True
            exclusions.append({"start_block": index, "end_block": index, "marker": flat})
            continue
        if in_toc:
            if PAGINATED_TOC_ROW.search(flat):
                exclusions[-1]["end_block"] = index
                continue
            in_toc = False
        result.append(block)
    return result, exclusions


def join_split_article_headings(blocks: list[str]) -> list[str]:
    """Join official HTML where the number and its punctuation/body are split."""
    out = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        if i + 1 < len(blocks) and STANDALONE_ARTICLE.fullmatch(str(block).strip()):
            following = str(blocks[i + 1]).strip()
            # Some publishers put the complete first sentence in the next DOM
            # element without a leading dot. Never consume a second heading.
            if following and not STANDALONE_ARTICLE.fullmatch(following) and not HEADING.match(following):
                merged = SourceBlock(f"{str(block).strip()} {following}",
                                     anchored=getattr(block, "anchored", False),
                                     page=getattr(block, "page", None))
                out.append(merged)
                i += 2
                continue
        out.append(block)
        i += 1
    return out


def _as_html(blocks: list[str], title: str = "") -> bytes:
    title_tag = f"<title>{escape(title)}</title>" if title else ""
    body = "".join(f"<p>{escape(str(block))}</p>" for block in blocks)
    return f"<html>{title_tag}<body>{body}</body></html>".encode("utf-8")


def parse_document_v02(meta: dict, data: bytes) -> tuple[str, list[dict], list[dict], list[dict], dict]:
    """Parse official bytes with the v0.2-only audit corrections."""
    decision = meta["source_type"] == "decision"
    if data.startswith(b"%PDF-"):
        blocks, title = blocks_from_pdf(data, meta.get("pdf_skip_pages", []))
    else:
        blocks, title = blocks_from_html(data, decision)
    exclusions = []
    if decision:
        blocks, exclusions = remove_decision_table_of_contents(blocks)
    else:
        blocks = join_split_article_headings(blocks)
    # The shared extractor reads sanitized source blocks, while source hashes
    # remain tied to the untouched official bytes held by the caller.
    sanitized = _as_html(blocks, title)
    clean, passages, nodes, edges, info = parse_document(
        meta, sanitized, source_blocks=blocks, source_title=title,
        source_is_pdf=data.startswith(b"%PDF-"), end_units_at_headings=not decision)
    info["parser_version"] = "legal-blocks-v02-audit-2"
    info["source_excluded_ranges"] = exclusions
    repealed_units = {}
    for passage in passages:
        passage["corpus_version"] = "corpus-v0.2"
        passage["parser_version"] = "legal-blocks-v02-audit-2"
        # Only a notice about this very article, close to its heading, is
        # actionable. A repeal mentioned later in a judgment or cross-reference
        # is not a status assertion about the containing article.
        body = passage["text"][len(passage["text_prefix"]):]
        heading = re.match(r"^\s*art[ií]culo\s+\S+\s*[.°º:ª-]?\s*([^\n]{0,220})", body, re.I)
        notice = PUBLISHER_REPEAL.search(heading.group(1)) if heading else None
        if notice and passage.get("article") is not None:
            repealed_units[passage["graph_node_ids"][1]] = heading.group(1)[notice.start():notice.end()]
    for passage in passages:
        notice = repealed_units.get(passage["graph_node_ids"][1])
        if notice:
            passage["publisher_repeal_notice"] = notice
            reasons = passage.setdefault("index_exclusion_reasons", [])
            if "publisher_repeal_notice" not in reasons:
                reasons.append("publisher_repeal_notice")
            passage["retrieval_eligible"] = False
    info["n_publisher_repeal_excluded"] = sum(
        "publisher_repeal_notice" in p.get("index_exclusion_reasons", []) for p in passages)
    info["n_indexed"] = sum(indexable(p) for p in passages)
    return clean, passages, nodes, edges, info
