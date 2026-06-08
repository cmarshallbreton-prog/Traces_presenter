import unittest

from src.xapi_progsnap2_translator.code_states import compute_code_states_id, extract_code_state, translate_statements_to_code_states_rows

from tests.helpers import make_run_debugger, make_run_program


class TestCodeStates(unittest.TestCase):
    def test_extract_code_state_reads_program_extension(self) -> None:
        """Extrait le code depuis object.extension (/Program)."""
        statement = make_run_program(code_state="print('hello')\n")
        self.assertEqual(extract_code_state(statement), "print('hello')\n")

    def test_compute_code_states_id_normalizes_newlines(self) -> None:
        """Le CodeStateID doit être identique malgré les variantes de newlines."""
        code_state = "print('hello')\r\nprint('world')\r"
        self.assertEqual(
            compute_code_states_id(code_state),
            compute_code_states_id(code_state.replace("\r\n", "\n").replace("\r", "\n")),
        )

    def test_translate_statements_to_code_states_rows_deduplicates_normalized_code(self) -> None:
        """Déduplique des CodeStates identiques une fois normalisés."""
        statements = [
            make_run_program(code_state="print('same')\r\n"),
            make_run_debugger(code_state="print('same')\n", lineno=7),
        ]

        rows = translate_statements_to_code_states_rows(statements)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Code"], "print('same')\r\n")
