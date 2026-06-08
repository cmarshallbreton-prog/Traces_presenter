import json
import unittest
from pathlib import Path

from src.xapi_progsnap2_translator.io import read_xapi_json


class TestIOErrors(unittest.TestCase):
    def test_read_xapi_json_raises_on_not_list(self):
        # Écrire un fichier JSON invalide dans un dossier de test pour faciliter l'inspection manuelle.
        run_dir = Path(__file__).resolve().parent / "fixtures" / "generated" / "io_errors"
        run_dir.mkdir(parents=True, exist_ok=True)
        p = run_dir / "bad.json"
        p.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
        with self.assertRaises(ValueError):
            read_xapi_json(p)

    def test_read_xapi_json_raises_on_non_object_element(self):
        run_dir = Path(__file__).resolve().parent / "fixtures" / "generated" / "io_errors"
        run_dir.mkdir(parents=True, exist_ok=True)
        p = run_dir / "bad2.json"
        p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        with self.assertRaises(ValueError):
            read_xapi_json(p)


if __name__ == '__main__':
    unittest.main()
