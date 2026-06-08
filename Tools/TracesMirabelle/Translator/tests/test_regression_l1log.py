import json
import csv
import os
import tempfile
import unittest
from pathlib import Path

from src.xapi_progsnap2_translator.main import translate_file


class TestRegressionL1Log(unittest.TestCase):
    def test_translate_real_l1log_file(self):
        fixture = os.path.join(os.path.dirname(__file__), "fixtures", "l1log_real.json")
        assert os.path.exists(fixture), f"Fixture not found: {fixture}"
        with open(fixture, encoding="utf-8") as fh:
            statements = json.load(fh)

        # Écrire l'entrée et les sorties dans un emplacement visible pour
        # faciliter l'inspection manuelle.
        run_dir = Path(__file__).resolve().parent / "fixtures" / "generated" / "l1log_run"
        run_dir.mkdir(parents=True, exist_ok=True)

        in_path = run_dir / "input.json"
        out_main = run_dir / "out" / "MainTable.csv"
        with open(in_path, "w", encoding="utf-8") as fh:
            json.dump(statements, fh)

        # exécuter le traducteur (convertir en Path uniquement lors de
        # l'appel de la fonction)
        main_path, link_path, code_path = translate_file(Path(in_path), Path(out_main))

        # les fichiers doivent exister
        self.assertTrue(os.path.exists(main_path))
        self.assertTrue(os.path.exists(link_path))
        self.assertTrue(os.path.exists(code_path))

        # charger la table principale et s'assurer qu'il y a au moins une ligne Run.Test
        with open(main_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        # construire la liste des lignes Run.Test
        run_tests = []
        for r in rows:
            if r.get("EventType") == "Run.Test":
                run_tests.append(r)

        self.assertTrue(run_tests, "No Run.Test rows found in MainTable.csv")

        # si X-RunTestData est présent, il doit être du JSON valide
        for r in run_tests:
            data = r.get("X-RunTestData") or ""
            if data:
                parsed = json.loads(data)
                self.assertIsInstance(parsed, list)


if __name__ == "__main__":
    unittest.main()
