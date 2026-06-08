import json
import unittest

from src.xapi_progsnap2_translator.main_table import (
    extract_output_error,
    extract_run_test_data,
    extract_session_id,
    handle_run_debugger,
    handle_run_program,
    handle_run_test,
    translate_statements_to_main_rows,
)

from tests.helpers import make_file_save, make_run_debugger, make_run_program, make_run_test


class TestMainTable(unittest.TestCase):
    def test_extract_session_id_reads_context_extension(self) -> None:
        """Lit Session.Id depuis context.extension (/Session/ID)."""
        self.assertEqual(extract_session_id(make_run_program(session_id="session-42")), "session-42")

    def test_extract_output_error_returns_stdout_and_stderr(self) -> None:
        """Extrait (stdout, stderr) depuis result.extension (/stdout, /stderr)."""
        output, error = extract_output_error(make_run_program(stdout="ok", stderr="boom", success=False))
        self.assertEqual(output, "ok")
        self.assertEqual(error, "boom")

    def test_handle_run_program_uses_one_status_column(self) -> None:
        """Écrit uniquement ExecutionResult (Success/Error), sans colonne redondante."""
        row = handle_run_program(make_run_program(success=True, stdout="hello\n"), 1, "Run.Program")
        self.assertEqual(row["ExecutionResult"], "Success")
        self.assertNotIn("RunProgram.Result", row)
        self.assertEqual(row["ProgramOutput"], "hello\n")
        self.assertEqual(row["ProgramErrorOutput"], "")

    def test_handle_run_program_failure_keeps_error_details(self) -> None:
        """En cas d'échec, conserve stdout et renseigne un type/message d'erreur."""
        row = handle_run_program(make_run_program(success=False, stdout="start\n", stderr="Traceback: boom"), 1, "Run.Program")
        self.assertEqual(row["ExecutionResult"], "Error")
        self.assertEqual(row["ProgramOutput"], "start\n")
        self.assertIn("Traceback", row["ProgramErrorOutput"])

    def test_extract_run_test_data_returns_json_string(self) -> None:
        """Retourne X-RunTestData sous forme de chaîne JSON décodable."""
        tests_json = extract_run_test_data(make_run_test())
        tests_data = json.loads(tests_json)
        self.assertEqual(tests_data[0]["verdict"], "PassedVerdict")

    def test_handle_run_test_puts_run_test_data_in_main_row(self) -> None:
        """Place X-RunTestData (JSON string) dans la colonne MainTable X-RunTestData."""
        row = handle_run_test(make_run_test(), 1, "Run.Test")
        self.assertEqual(row["X-RunTestData"], extract_run_test_data(make_run_test()))

    def test_handle_run_debugger_includes_lineno(self) -> None:
        """Debug.Program remplit Lineno et les champs d'exécution (résultat)."""
        row = handle_run_debugger(make_run_debugger(lineno=12), 1, "Debug.Program")
        self.assertEqual(row["Lineno"], "12")
        self.assertEqual(row["ExecutionResult"], "Success")

    def test_translate_statements_to_main_rows_filters_irrelevant_events(self) -> None:
        """Filtre les événements non supportés et conserve l'ordre des events supportés."""
        rows = translate_statements_to_main_rows([make_run_program(), make_run_test(), make_run_debugger(), make_file_save()])
        self.assertEqual(len(rows), 4)
        
        # Construire la liste des types d'événements
        event_types = []
        for row in rows:
            event_types.append(row["EventType"])

        self.assertEqual(event_types, ["Run.Program", "Run.Test", "Debug.Program", "X-File.Save"])
