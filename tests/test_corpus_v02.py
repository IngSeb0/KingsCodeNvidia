import json
import re
import unittest
from pathlib import Path

from kingscode.corpus import blocks_from_html
from kingscode.diversify import collapse_duplicates
from kingscode.corpus_v02 import (
    join_split_article_headings, parse_document_v02, remove_decision_table_of_contents,
)
from kingscode.metadata import canonical_fragment_id
from kingscode.metadata import canonical_document_id

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures" / "corpus_v02"


def meta(doc_id, source_type, norm_name, number, year, canonical_body, url):
    return {
        "doc_id": doc_id, "source_type": source_type, "norm_name": norm_name,
        "norm_number": number, "year": year, "canonical_body": canonical_body,
        "source_url": url, "source_sha256": "fixture-source-sha256",
        "retrieved_at": "2026-09-29T00:00:00Z", "areas": ["Derecho constitucional"],
    }


class CorpusV02SourceRepairTests(unittest.TestCase):
    def test_d01_content_collapse_preserves_all_seven_distinct_decision_groups(self):
        findings = [json.loads(line) for line in
                    (ROOT / ".." / "reports" / "member_a_v02" / "corpus_audit_findings_v07.jsonl")
                    .read_text(encoding="utf-8-sig").splitlines()]
        d01 = next(row for row in findings if row["finding_id"] == "D01")
        groups = d01["evidence"]
        self.assertEqual(len(groups), 7)
        observed_documents = 0
        for group in groups:
            expected = group["canonical_documents"]
            self.assertGreater(len(expected), 1)
            self.assertEqual(len(set(expected)), len(expected))
            rows = []
            for index, document_id in enumerate(expected):
                court, compact_docket, year = document_id.split(":")
                match = re.fullmatch(r"([a-z]+)(\d+)", compact_docket)
                self.assertEqual(court, "corte_constitucional")
                self.assertIsNotNone(match, document_id)
                docket = f"{match.group(1).upper()}-{match.group(2)}"
                rows.append({
                    "passage_id": f"{document_id}:d01:{index}",
                    "doc_id": f"sentencia_{match.group(1)}_{match.group(2)}_de_{year}",
                    "source_type": "decision",
                    "canonical_body": ["jurisprudencia", docket, year],
                    "text": group["body"],
                    "source_url": f"https://official.example/{document_id}",
                })
            self.assertEqual({canonical_document_id(row) for row in rows}, set(expected))
            collapsed = collapse_duplicates(rows, level="content")
            self.assertEqual({canonical_document_id(row) for row in collapsed}, set(expected))
            self.assertTrue(all(len(row["duplicate_group"]["members"]) == 1 for row in collapsed))
            observed_documents += len(expected)
        self.assertEqual(observed_documents, 22)

    def test_g01_rejected_container_targets_never_activate_uncertain_relations(self):
        review = json.loads((ROOT / ".." / "reports" / "member_a_v02" /
                             "g01_relation_review_v02.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(review["source_candidate_count"], 7)
        self.assertEqual(review["rejected_wrong_container_target"], 7)
        self.assertEqual(review["replacement_relations_unresolved"], 7)
        self.assertEqual(review["accepted_semantic_relations"], 0)
        self.assertEqual(review["active_semantic_edges"], 0)
        for relation in review["relations"]:
            self.assertEqual(relation["candidate_disposition"], "REJECTED_WRONG_CONTAINER_TARGET")
            self.assertFalse(relation["replacement_relation_active"])
            self.assertEqual(relation["replacement_relation_status"],
                             "UNRESOLVED_REFERENCED_PRIMARY_BYTES_NOT_ACQUIRED")

    def test_fixtures_match_preserved_official_source_blocks(self):
        spans = __import__("json").loads((FIXTURES / "source_spans.json").read_text(encoding="utf-8-sig"))
        raw_root = ROOT.parent / "corpora" / "corpus-v0.2" / "raw"
        source_files = {
            "G02-SU214-TOC": ("sentencia_su_214_de_2016.html", "g02_su214_toc.txt", True),
            "C01-C355-REPEATED-HEADING": ("sentencia_c_355_de_2006.html", "c01_c355_sections.txt", True),
            "P02-LEY137-SPLIT-ARTICLE": ("ley_137_de_1994.html", "p02_ley137_articles.txt", False),
            "P01-LEY137-HEADING-BOUNDARY": ("ley_137_de_1994.html", "p01_ley137_heading_boundary.txt", False),
        }
        for fixture in spans["fixtures"]:
            filename, excerpt, decision = source_files[fixture["id"]]
            source_blocks, _ = blocks_from_html((raw_root / filename).read_bytes(), decision)
            expected = [source_blocks[i] for i in fixture["source_block_indices"]]
            actual = (FIXTURES / excerpt).read_text(encoding="utf-8-sig").splitlines()
            self.assertEqual(actual, expected, fixture["id"])

    def test_g02_removes_only_paginated_toc_rows(self):
        blocks = (FIXTURES / "g02_su214_toc.txt").read_text(encoding="utf-8-sig").splitlines()
        clean, excluded = remove_decision_table_of_contents(blocks)
        self.assertEqual(len(excluded), 1)
        self.assertNotIn("RESUELVE 201", clean)
        self.assertIn("ACLARACIÓN DE VOTO DEL MAGISTRADO", clean)
        self.assertIn("RESUELVE", clean)
        self.assertTrue(any(row.startswith("PRIMERO.") for row in clean))

    def test_c01_same_heading_occurrences_keep_distinct_fragment_ids(self):
        blocks = (FIXTURES / "c01_c355_sections.txt").read_text(encoding="utf-8-sig").splitlines()
        source = "<html><title>C-355</title><body><article><p>CONSIDERACIONES</p>" + "".join(f"<p>{b}</p>" for b in blocks) + "</article></body></html>"
        _, passages, _, _, info = parse_document_v02(
            meta("sentencia_c_355_de_2006", "decision", "Sentencia C-355 de 2006", "C-355", 2006,
                 ["jurisprudencia", "C-355", "2006"], "https://www.corteconstitucional.gov.co/relatoria/2006/c-355-06.htm"),
            source.encode("utf-8"),
        )
        matching = [p for p in passages if p["section"] == "Fundamentos lógicos"]
        self.assertEqual(len(matching), 3)
        ids = [canonical_fragment_id(p) for p in matching]
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual(len({p["source_unit_id"] for p in matching}), 3)

    def test_p02_joins_split_article_number_and_body(self):
        blocks = (FIXTURES / "p02_ley137_articles.txt").read_text(encoding="utf-8-sig").splitlines()
        joined = join_split_article_headings(blocks)
        self.assertEqual(len(joined), 2)
        self.assertEqual(len(join_split_article_headings(["Artículo 40", "CAPÍTULO IV", "Artículo 41"])), 3)
        self.assertTrue(str(joined[0]).startswith("Artículo 40 . Concepto favorable"))
        source = "<html><body><div class=\"descripcion-contenido\">" + "".join(f"<p>{b}</p>" for b in blocks) + "</div></body></html>"
        _, passages, _, _, _ = parse_document_v02(
            meta("ley_137_de_1994", "law", "Ley 137 de 1994", "137", 1994,
                 ["ley", "137", "1994"], "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=13966"),
            source.encode("utf-8"),
        )
        self.assertEqual([p["article"] for p in passages], ["40", "41"])

    def test_split_heading_without_leading_punctuation(self):
        blocks = ["Artículo 40", "Concepto favorable del Senado para una decisión.",
                  "Artículo 41", "La autoridad deberá motivar el acto."]
        joined = join_split_article_headings(blocks)
        self.assertEqual(len(joined), 2)
        source = "<html><body><div class='descripcion-contenido'>" + "".join(f"<p>{b}</p>" for b in blocks) + "</div></body></html>"
        _, passages, _, _, _ = parse_document_v02(
            meta("ley_demo", "law", "Ley Demo", "1", 2024,
                 ["ley", "1", "2024"], "https://www.funcionpublica.gov.co/"), source.encode())
        self.assertEqual([p["article"] for p in passages], ["40", "41"])

    def test_explicit_publisher_repeal_excludes_only_its_article(self):
        source = ("<html><body><div class='descripcion-contenido'><p>ARTÍCULO 76. Derogado por el artículo 1 de la Ley 2 de 2011.</p>"
                  "<p>Texto anterior extenso.</p><p>ARTÍCULO 77. Esta regla sigue en el texto.</p>"
                  "</div></body></html>")
        _, passages, _, _, info = parse_document_v02(
            meta("ley_demo", "law", "Ley Demo", "1", 2024,
                 ["ley", "1", "2024"], "https://www.funcionpublica.gov.co/"), source.encode())
        article76 = [p for p in passages if p["article"] == "76"]
        article77 = [p for p in passages if p["article"] == "77"]
        self.assertTrue(article76)
        self.assertTrue(all(not p["retrieval_eligible"] for p in article76))
        self.assertTrue(all(p["retrieval_eligible"] for p in article77))
        self.assertEqual(info["n_publisher_repeal_excluded"], len(article76))

    def test_incidental_repeal_reference_does_not_exclude_containing_article(self):
        source = ("<html><body><div class='descripcion-contenido'><p>ARTÍCULO 69. La contratación se regirá por estas reglas.</p>"
                  "<p>El artículo 227 del Decreto 1818 de 1998 fue derogado por otra ley.</p>"
                  "<p>La referencia anterior no modifica este artículo.</p>"
                  "</div></body></html>")
        _, passages, _, _, info = parse_document_v02(
            meta("ley_demo", "law", "Ley Demo", "1", 2024,
                 ["ley", "1", "2024"], "https://www.funcionpublica.gov.co/"), source.encode())
        self.assertTrue(all(p["retrieval_eligible"] for p in passages))
        self.assertEqual(info["n_publisher_repeal_excluded"], 0)

    def test_publisher_repeal_notice_after_angle_title(self):
        source = ("<html><body><div class='descripcion-contenido'>"
                  "<p>ARTÍCULO 2131. &lt;DERECHOS&gt;. &lt;Artículo derogado por el artículo 242 de la Ley 222 de 1995&gt;</p>"
                  "<p>Texto editorial adicional.</p><p>ARTÍCULO 2132. Otro precepto.</p>"
                  "</div></body></html>")
        _, passages, _, _, info = parse_document_v02(
            meta("ley_demo", "law", "Ley Demo", "1", 2024,
                 ["ley", "1", "2024"], "https://www.funcionpublica.gov.co/"), source.encode())
        self.assertEqual(info["n_publisher_repeal_excluded"], 1)
        self.assertFalse(next(p for p in passages if p["article"] == "2131")["retrieval_eligible"])

    def test_p01_major_heading_closes_prior_article(self):
        blocks = (FIXTURES / "p01_ley137_heading_boundary.txt").read_text(encoding="utf-8-sig").splitlines()
        source = "<html><body><div class=\"descripcion-contenido\">" + "".join(f"<p>{b}</p>" for b in blocks) + "</div></body></html>"
        _, passages, _, _, _ = parse_document_v02(
            meta("ley_137_de_1994", "law", "Ley 137 de 1994", "137", 1994,
                 ["ley", "137", "1994"], "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=13966"),
            source.encode("utf-8"),
        )
        article45 = next(p for p in passages if p["article"] == "45")
        article46 = next(p for p in passages if p["article"] == "46")
        self.assertNotIn("CAPITULO IV", article45["text"])
        self.assertNotIn("Del Estado de Emergencia", article45["text"])
        self.assertIn("CAPITULO IV", article46["hierarchy_path"])


if __name__ == "__main__":
    unittest.main()
