import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.xapi_progsnap2_translator.main import translate_file

from tests.helpers import make_multi_user_statements, make_run_debugger, make_run_program, make_run_test


class TestIntegration(unittest.TestCase):
    def test_translate_file_writes_the_three_csv_tables(self) -> None:
        """Traduit un JSON xAPI multi-users et valide le contenu des 3 CSV."""
        statements = make_multi_user_statements()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.json"
            output_main = temp_path / "out" / "MainTable.csv"
            input_path.write_text(json.dumps(statements), encoding="utf-8")

            main_path, link_path, code_states_path = translate_file(input_path, output_main)

            with main_path.open(encoding="utf-8", newline="") as handle:
                main_rows = list(csv.DictReader(handle))
            with link_path.open(encoding="utf-8", newline="") as handle:
                link_rows = list(csv.DictReader(handle))
            with code_states_path.open(encoding="utf-8", newline="") as handle:
                code_rows = list(csv.DictReader(handle))

        self.assertEqual(len(main_rows), 4)
        self.assertEqual(len(link_rows), 2)
        self.assertEqual(len(code_rows), 2)

        # LinkTable: association SubjectID (anonymisé) <-> Identifier (non anonymisé)
        # Construire le mapping avec une boucle simple pour améliorer la lisibilité.
        subject_by_identifier = {}
        for row in link_rows:
            subject_by_identifier[row["X-Identifier"]] = row["SubjectID"]

        # S'attendre exactement à ces identifiants (l'ordre n'a pas d'importance).
        self.assertCountEqual(list(subject_by_identifier.keys()), ["alice", "bob"])
        self.assertTrue(all(subject_by_identifier.values()))

        # MainTable: 4 événements attendus, et aucune colonne redondante.
        # Collecter les types d'événements uniques avec une boucle explicite
        # (plus facile à suivre).
        event_types = []
        for row in main_rows:
            et = row["EventType"]
            if et not in event_types:
                event_types.append(et)

        self.assertCountEqual(event_types, ["Run.Program", "Run.Test", "Debug.Program", "X-File.Save"])
        self.assertTrue(all("RunProgram.Result" not in row for row in main_rows))

        # Mapper type d'événement -> ligne pour faciliter les assertions ci‑dessous.
        main_by_type = {}
        for row in main_rows:
            main_by_type[row["EventType"]] = row

        # Run.Program (alice): succès + stdout dans la bonne colonne.
        run_program = main_by_type["Run.Program"]
        self.assertEqual(run_program["SubjectID"], subject_by_identifier["alice"])
        self.assertEqual(run_program["ExecutionResult"], "Success")
        self.assertEqual(run_program["ProgramOutput"], "ok\n")
        self.assertEqual(run_program["ProgramErrorOutput"], "")

        # Debug.Program (bob): échec + lineno + stderr dans la bonne colonne.
        run_debugger = main_by_type["Debug.Program"]
        self.assertEqual(run_debugger["SubjectID"], subject_by_identifier["bob"])
        self.assertEqual(run_debugger["Lineno"], "3")
        self.assertEqual(run_debugger["ExecutionResult"], "Error")
        self.assertEqual(run_debugger["ProgramOutput"], "step\n")
        self.assertIn("Traceback", run_debugger["ProgramErrorOutput"])

        # Run.Test (alice): X-RunTestData doit être un JSON décodable.
        run_test = main_by_type["Run.Test"]
        self.assertEqual(run_test["SubjectID"], subject_by_identifier["alice"])
        tests_data = json.loads(run_test["X-RunTestData"])
        self.assertIsInstance(tests_data, list)
        self.assertEqual(tests_data[0]["verdict"], "PassedVerdict")

        # CodeStates: les CodeStateID de la MainTable doivent tous exister dans CodeStates.
        # CodeStates : collecter les IDs et vérifier l'appartenance avec des
        # boucles simples.
        code_state_ids = []
        for row in code_rows:
            if row["CodeStateID"] not in code_state_ids:
                code_state_ids.append(row["CodeStateID"])

        self.assertTrue(code_state_ids)

        for row in main_rows:
            if row["CodeStateID"]:
                self.assertIn(row["CodeStateID"], code_state_ids)

        # Vérifier le contenu du code et les identifiants (listes explicites
        # pour la lisibilité).
        code_contents = []
        for row in code_rows:
            if row["Code"] not in code_contents:
                code_contents.append(row["Code"])
        self.assertCountEqual(code_contents, ["print('shared')\r\n", "print('tests')\n"])

        identifiers = []
        for row in link_rows:
            if row["X-Identifier"] not in identifiers:
                identifiers.append(row["X-Identifier"])
        self.assertCountEqual(identifiers, ["alice", "bob"])

        # Vérifier les valeurs de résultat pour RunProgram/Debug.Program.
        run_program_results = []
        for row in main_rows:
            if row["EventType"] == "Run.Program" and row["ExecutionResult"] not in run_program_results:
                run_program_results.append(row["ExecutionResult"])
        self.assertCountEqual(run_program_results, ["Success"])

        run_debugger_results = []
        for row in main_rows:
            if row["EventType"] == "Debug.Program" and row["ExecutionResult"] not in run_debugger_results:
                run_debugger_results.append(row["ExecutionResult"])
        self.assertCountEqual(run_debugger_results, ["Error"])

    def test_translate_file_handles_binome_openid_with_multiple_actors(self) -> None:
        """Vérifie qu'un openid de type user1/user2 est attribué à user1 dans un flux multi-acteurs."""
        statements = [
            make_run_program(user="user1/user2", code_state="print('a')\n", success=True, stdout="a\n", session_id="s-1"),
            make_run_test(user="user1/user2", code_state="print('tests')\n"),
            make_run_debugger(user="bob/partner", code_state="print('b')\n", lineno=2, success=False, stdout="dbg\n", stderr="Traceback: b"),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "input.json"
            output_main = temp_path / "out" / "MainTable.csv"
            input_path.write_text(json.dumps(statements), encoding="utf-8")

            main_path, link_path, _ = translate_file(input_path, output_main)

            with main_path.open(encoding="utf-8", newline="") as handle:
                main_rows = list(csv.DictReader(handle))
            with link_path.open(encoding="utf-8", newline="") as handle:
                link_rows = list(csv.DictReader(handle))

        self.assertEqual(len(main_rows), 3)
        self.assertEqual(len(link_rows), 2)

        subject_by_identifier = {row["X-Identifier"]: row["SubjectID"] for row in link_rows}
        self.assertEqual(set(subject_by_identifier.keys()), {"user1", "bob"})

        run_program_rows = [row for row in main_rows if row["EventType"] == "Run.Program"]
        run_test_rows = [row for row in main_rows if row["EventType"] == "Run.Test"]
        run_debugger_rows = [row for row in main_rows if row["EventType"] == "Debug.Program"]

        self.assertEqual(len(run_program_rows), 1)
        self.assertEqual(len(run_test_rows), 1)
        self.assertEqual(len(run_debugger_rows), 1)

        self.assertEqual(run_program_rows[0]["SubjectID"], subject_by_identifier["user1"])
        self.assertEqual(run_test_rows[0]["SubjectID"], subject_by_identifier["user1"])
        self.assertEqual(run_debugger_rows[0]["SubjectID"], subject_by_identifier["bob"])
