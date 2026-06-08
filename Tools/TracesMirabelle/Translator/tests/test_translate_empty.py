import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.xapi_progsnap2_translator.main import translate_file


class TestTranslateEmpty(unittest.TestCase):
    def test_translate_file_with_empty_list_writes_headers_only(self):
        # Utiliser un dossier visible pour l'entrée/sortie
        run_dir = Path(__file__).resolve().parent / "fixtures" / "generated" / "empty_run"
        run_dir.mkdir(parents=True, exist_ok=True)

        inp = run_dir / "in.json"
        out_main = run_dir / "out" / "MainTable.csv"
        inp.write_text(json.dumps([]), encoding="utf-8")

        main_path, link_path, code_states_path = translate_file(inp, out_main)

        # chaque CSV doit exister et ne contenir que l'en-tête (pas de lignes de données)
        for path in (main_path, link_path, code_states_path):
            with path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
                self.assertEqual(len(rows), 0)


if __name__ == '__main__':
    unittest.main()
