import filecmp
import json
import os
import unittest
import csv
from pathlib import Path

from src.xapi_progsnap2_translator.main import translate_file


class TestCompareExpectedAliceBob(unittest.TestCase):
    def test_generated_equals_expected(self):
        fixture = os.path.join(os.path.dirname(__file__), "fixtures", "alice_bob_demo.json")
        assert os.path.exists(fixture)
        with open(fixture, encoding="utf-8") as fh:
            statements = json.load(fh)

        # Placer les entrées et sorties dans un dossier de test visible afin
        # que les CSV générés puissent être inspectés manuellement.
        run_dir = Path(__file__).resolve().parent / "fixtures" / "generated" / "alice_bob_run"
        run_dir.mkdir(parents=True, exist_ok=True)

        in_path = run_dir / "input.json"
        out_main = run_dir / "MainTable.csv"
        with open(in_path, "w", encoding="utf-8") as fh:
            json.dump(statements, fh)

        # exécuter le traducteur
        main_path, link_path, code_path = translate_file(Path(in_path), Path(out_main))

        # comparer aux fichiers attendus
        expected_dir = Path(__file__).resolve().parent / "expected" / "alice_bob"
        self.assertTrue(expected_dir.exists())

        # Compare CSV content semantically to avoid false negatives caused by
        # platform-dependent newline differences or minor quoting variations.
        def _read_csv_rows(p):
            with open(p, encoding="utf-8", newline="") as fh:
                reader = csv.reader(fh)
                return [row for row in reader]

        self.assertEqual(_read_csv_rows(main_path), _read_csv_rows(expected_dir / "MainTable.csv"), "MainTable.csv differs from expected")
        self.assertEqual(_read_csv_rows(link_path), _read_csv_rows(expected_dir / "LinkTable.csv"), "LinkTable.csv differs from expected")
        self.assertEqual(_read_csv_rows(code_path), _read_csv_rows(expected_dir / "CodeStates.csv"), "CodeStates.csv differs from expected")


if __name__ == "__main__":
    unittest.main()
