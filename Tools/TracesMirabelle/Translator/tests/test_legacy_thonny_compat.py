import json
import csv
import os
import unittest
from pathlib import Path

from src.xapi_progsnap2_translator.main import translate_file


def _make_legacy_statement():    
    return {
        "timestamp": "2024-05-28T10:38:36.402700",
        "research_usage": True,
        "verb": {"id": "https://www.cristal.univ-lille.fr/verbs/Run.Test"},
        "actor": {"openid": "https://www.cristal.univ-lille.fr/users/user1/"},
        "object": {
            "id": "https://www.cristal.univ-lille.fr/objects/Tests",
            "extension": {
                "https://www.cristal.univ-lille.fr/objects/File/Filename": "C:/file.py",
                "https://www.cristal.univ-lille.fr/objects/Tests/Tests": [
                    {
                        "filename": "C:/file.py",
                        "lineno": 8,
                        "tested_line": "foo()",
                        "expected_result": '"foo"',
                        "details": "",
                        "verdict": "FailedVerdict",
                        "name": "foo()",
                        "status": False,
                    }
                ],
                "https://www.cristal.univ-lille.fr/objects/Tests/Status": True,
                "https://www.cristal.univ-lille.fr/objects/Tests/Error": None,
                "https://www.cristal.univ-lille.fr/objects/Program/CodeState": "print(\"hi\")",
            },
        },
        "context": {"extension": {"https://www.cristal.univ-lille.fr/objects/Session/ID": "42"}},
    }


class TestLegacyThonnyCompat(unittest.TestCase):
    def test_translate_legacy_thonny_statement(self):
        stmt = _make_legacy_statement()

        run_dir = Path(__file__).resolve().parent / "fixtures" / "generated" / "legacy_run"
        run_dir.mkdir(parents=True, exist_ok=True)

        in_path = run_dir / "input.json"
        out_main = run_dir / "out" / "MainTable.csv"

        with open(in_path, "w", encoding="utf-8") as fh:
            json.dump([stmt], fh)

        main_path, link_path, code_path = translate_file(Path(in_path), Path(out_main))

        # Les fichiers doivent exister
        self.assertTrue(os.path.exists(main_path))
        self.assertTrue(os.path.exists(link_path))
        self.assertTrue(os.path.exists(code_path))

        # Vérifier qu'il y a une ligne Run.Test
        with open(main_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        types = [r.get("EventType") for r in rows]
        self.assertIn("Run.Test", types)


if __name__ == "__main__":
    unittest.main()
