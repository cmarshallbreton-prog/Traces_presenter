import unittest

from src.xapi_progsnap2_translator.utils import coerce_cell_text, extract_primary_user_from_openid, normalize_newlines, sha256_hex


class TestUtils(unittest.TestCase):
    def test_extract_primary_user_from_openid_uses_first_segment(self) -> None:
        """Découpe l'openid et ne conserve que le premier segment user."""
        self.assertEqual(
            extract_primary_user_from_openid("https://www.cristal.univ-lille.fr/users/user1/user2/"),
            "user1",
        )

    def test_extract_primary_user_from_openid_handles_plain_value(self) -> None:
        """Accepte aussi les valeurs non-URL (ex: 'user1/user2')."""
        self.assertEqual(extract_primary_user_from_openid("user1/user2"), "user1")

    def test_sha256_hex_is_stable(self) -> None:
        """Le hash doit être déterministe (même input → même output)."""
        self.assertEqual(sha256_hex("abc"), sha256_hex("abc"))

    def test_normalize_newlines_collapses_windows_and_mac(self) -> None:
        """Normalise '\\r\\n' et '\\r' en '\\n'."""
        self.assertEqual(normalize_newlines("a\r\nb\rc"), "a\nb\nc")

    def test_coerce_cell_text_encodes_structures_as_compact_json(self) -> None:
        """Les valeurs non-string sont encodées en JSON compact pour les cellules CSV."""
        self.assertEqual(coerce_cell_text([{"lineno": 1, "verdict": "PassedVerdict"}]), '[{"lineno":1,"verdict":"PassedVerdict"}]')
