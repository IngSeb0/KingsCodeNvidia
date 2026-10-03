import importlib.util
import unittest

from kingscode.common import ROOT


SPEC = importlib.util.spec_from_file_location("citation_pipeline_diagnostic", ROOT / "tools/diagnose_citation_pipeline.py")
DIAGNOSTIC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DIAGNOSTIC)


class CitationPipelineDiagnosticTests(unittest.TestCase):
    def test_separates_missing_evidence_context_truncation_and_omitted_citation(self):
        target = ("ley", "1010", "2006")
        absent = ("ley", "472", "1998")
        result = DIAGNOSTIC.classify(
            expected={target, absent},
            supported={target},
            dropped={absent},
            cited=set(),
        )
        self.assertEqual(result["available_but_not_cited"], {target})
        self.assertEqual(result["dropped_for_context"], {absent})
        self.assertEqual(result["missing_from_evidence"], set())
        self.assertEqual(result["cited_and_supported"], set())


if __name__ == "__main__":
    unittest.main()
