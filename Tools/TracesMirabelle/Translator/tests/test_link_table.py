import unittest

from src.xapi_progsnap2_translator.link_table import get_anonymized_subject_id, translate_statements_to_link_rows

from tests.helpers import make_file_save, make_run_debugger, make_run_program


class TestLinkTable(unittest.TestCase):
    def test_get_anonymized_subject_id_hashes_primary_user_only(self) -> None:
        """L'anonymisation ne dépend que du user principal (avant '/')."""
        statement = make_run_program(user="alice/binome")
        comparison = make_run_program(user="alice/another", code_state="x = 1\n")
        self.assertEqual(get_anonymized_subject_id(statement), get_anonymized_subject_id(comparison))

    def test_translate_statements_to_link_rows_keeps_unique_users_only(self) -> None:
        """La LinkTable contient une entrée par user unique (SubjectID)."""
        statements = [
            make_run_program(user="alice"),
            make_run_debugger(user="bob"),
            make_file_save(user="alice"),
        ]

        rows = translate_statements_to_link_rows(statements)
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["X-Identifier"] for row in rows}, {"alice", "bob"})
