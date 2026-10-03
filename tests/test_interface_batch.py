from __future__ import annotations

import json
import unittest

from interfaz.batch_io import parse_questions_jsonl, submissions_jsonl
from kingscode.reasoning.contracts import Question
from kingscode.reasoning.decoder import abstention_row


class InterfaceBatchInputTests(unittest.TestCase):
    def test_parser_allowlists_public_fields_and_supports_utf8_bom(self):
        record = {
            "id": 51,
            "pregunta": "¿Cuál es la regla aplicable?",
            "formato": "multiple_choice",
            "opciones": {"A": "Primera", "B": "Segunda", "C": "Tercera", "D": "Cuarta"},
            "expected_answer": "CANARY",
            "legal_basis": ["CANARY"],
        }
        questions = parse_questions_jsonl(("\ufeff" + json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8"))
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].public_record(), {
            "id": 51,
            "pregunta": "¿Cuál es la regla aplicable?",
            "formato": "multiple_choice",
            "opciones": {"A": "Primera", "B": "Segunda", "C": "Tercera", "D": "Cuarta"},
        })
        self.assertNotIn("CANARY", repr(questions[0].public_record()))

    def test_parser_reports_line_and_rejects_duplicate_or_incomplete_items(self):
        with self.assertRaisesRegex(ValueError, "Línea 2: JSON inválido"):
            parse_questions_jsonl(b"\nno-json\n")
        question = {"id": 7, "pregunta": "Consulta", "formato": "semi_open"}
        with self.assertRaisesRegex(ValueError, "id 7 está duplicado"):
            parse_questions_jsonl((json.dumps(question) + "\n" + json.dumps(question)).encode())
        invalid_choice = {**question, "formato": "multiple_choice", "opciones": {"A": "uno"}}
        with self.assertRaisesRegex(ValueError, "faltan opciones completas"):
            parse_questions_jsonl(json.dumps(invalid_choice).encode())

    def test_submission_serializer_sorts_and_validates_rows(self):
        rows = [
            abstention_row(Question(9, "Consulta nueve", "semi_open"), [], "test"),
            abstention_row(Question(2, "Consulta dos", "semi_open"), [], "test"),
        ]
        serialized = submissions_jsonl(rows).decode("utf-8").splitlines()
        self.assertEqual([json.loads(line)["id"] for line in serialized], [2, 9])
        self.assertTrue(all(line.endswith("}") for line in serialized))


if __name__ == "__main__":
    unittest.main()
