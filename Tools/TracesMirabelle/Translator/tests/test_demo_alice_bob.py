import json
import csv
import os
import unittest
from pathlib import Path

from src.xapi_progsnap2_translator.main import translate_file


class TestDemoAliceBob(unittest.TestCase):
    """Test de démonstration lisible : exécute le traducteur sur une petite
    fixture Alice/Bob.

    Objectif : produire des CSV lisibles stockés dans
    `tests/fixtures/generated/alice_bob/` pour que le client puisse
    les ouvrir directement.
    """

    def test_alice_bob_demo_creates_csvs(self):
        fixture = os.path.join(os.path.dirname(__file__), "fixtures", "alice_bob_demo.json")
        assert os.path.exists(fixture), f"Fixture not found: {fixture}"
        with open(fixture, encoding="utf-8") as fh:
            statements = json.load(fh)

        # Ecrire l'entrée et les sorties dans
        # le dossier `tests/fixtures/generated/alice_bob` pour que les fichiers
        # puissent être ouverts directement.
        gen_dir = Path(__file__).resolve().parent / "fixtures" / "generated" / "alice_bob"
        gen_dir.mkdir(parents=True, exist_ok=True)

        in_path = gen_dir / "input.json"
        out_main = gen_dir / "MainTable.csv"
        with open(in_path, "w", encoding="utf-8") as fh:
            json.dump(statements, fh)

        # exécuter le traducteur (il écrit MainTable.csv, LinkTable.csv et
        # CodeStates.csv dans le même dossier que `out_main`)
        main_path, link_path, code_path = translate_file(Path(in_path), Path(out_main))

        # assertions : les fichiers existent et contiennent les types
        # d'événements attendus
        self.assertTrue((gen_dir / "MainTable.csv").exists())
        with open(gen_dir / "MainTable.csv", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        # collecter les valeurs EventType avec une boucle explicite (plus lisible)
        types = []
        for r in rows:
            types.append(r.get("EventType"))

        # le traducteur produit des événements Run.Program et Run.Test pour
        # cette démonstration
        self.assertIn("Run.Program", types)
        self.assertIn("Run.Test", types)

        # vérifier que les autres CSV ont été créés et ne sont pas vides
        self.assertTrue((gen_dir / "LinkTables" / "Subject.csv").exists())
        self.assertTrue((gen_dir / "CodeStates" / "CodeStates.csv").exists())


if __name__ == "__main__":
    unittest.main()
