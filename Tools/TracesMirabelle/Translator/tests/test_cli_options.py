import csv
import json
import os
import unittest
from pathlib import Path

from src.xapi_progsnap2_translator.main import build_arg_parser, main as cli_main


class TestCliOptions(unittest.TestCase):
    def test_parser_uses_output_directory_and_separator(self) -> None:
        args = build_arg_parser().parse_args(["input.json", "-o", "out", "-sep", ";"])
        self.assertEqual(args.input, "input.json")
        self.assertEqual(args.o, "out")
        self.assertEqual(args.separator, ";")

    def test_parser_accepts_flags_in_any_order(self) -> None:
        args = build_arg_parser().parse_args(["input.json", "-sep", ";", "-o", "out"])
        self.assertEqual(args.input, "input.json")
        self.assertEqual(args.o, "out")
        self.assertEqual(args.separator, ";")

    def test_cli_writes_csv_with_custom_separator(self) -> None:
        fixture = os.path.join(os.path.dirname(__file__), "fixtures", "alice_bob_demo.json")
        self.assertTrue(os.path.exists(fixture), f"Fixture not found: {fixture}")
        with open(fixture, encoding="utf-8") as fh:
            statements = json.load(fh)

        output_dir = Path(__file__).resolve().parent / "fixtures" / "generated" / "cli_options"
        output_dir.mkdir(parents=True, exist_ok=True)

        input_path = output_dir / "input.json"
        with open(input_path, "w", encoding="utf-8") as fh:
            json.dump(statements, fh)

        cli_main([str(input_path), "-o", str(output_dir), "-sep", ";"])

        main_table = output_dir / "MainTable.csv"
        self.assertTrue(main_table.exists())

        with open(main_table, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh, delimiter=";"))

        self.assertGreater(len(rows), 0)
        self.assertIn("Run.Program", [row["EventType"] for row in rows])
        self.assertTrue((output_dir / "LinkTables" / "Subject.csv").exists())
        self.assertTrue((output_dir / "CodeStates" / "CodeStates.csv").exists())


if __name__ == "__main__":
    unittest.main()
