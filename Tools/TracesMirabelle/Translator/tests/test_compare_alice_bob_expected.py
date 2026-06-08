import csv
import json
import os
import tempfile
import unittest
from pathlib import Path

from src.xapi_progsnap2_translator.main import translate_file


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh))


class TestCompareAliceBobExpected(unittest.TestCase):
    def test_generated_matches_expected(self):
        fixture = os.path.join(os.path.dirname(__file__), "fixtures", "alice_bob_demo.json")
        expected_dir = Path(__file__).resolve().parent / "expected" / "alice_bob"
        assert os.path.exists(fixture)

        with open(fixture, encoding="utf-8") as fh:
            statements = json.load(fh)

        # Utiliser un dossier d'exécution visible pour que les CSV générés
        # puissent être inspectés.
        run_dir = Path(__file__).resolve().parent / "fixtures" / "generated" / "alice_bob_compare"
        run_dir.mkdir(parents=True, exist_ok=True)

        in_path = run_dir / "input.json"
        out_main = run_dir / "out" / "MainTable.csv"
        with open(in_path, "w", encoding="utf-8") as fh:
            json.dump(statements, fh)

        main_path, link_path, code_path = translate_file(Path(in_path), Path(out_main))

        # comparer les lignes pour chaque CSV
        expected_main = read_rows(expected_dir / "MainTable.csv")
        generated_main = read_rows(main_path)
        self.assertEqual(expected_main, generated_main)

        expected_link = read_rows(expected_dir / "LinkTable.csv")
        generated_link = read_rows(link_path)
        self.assertEqual(expected_link, generated_link)

        expected_code = read_rows(expected_dir / "CodeStates.csv")
        generated_code = read_rows(code_path)
        self.assertEqual(expected_code, generated_code)


if __name__ == "__main__":
    unittest.main()
