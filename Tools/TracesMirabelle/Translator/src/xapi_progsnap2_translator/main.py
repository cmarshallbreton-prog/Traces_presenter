import argparse
from pathlib import Path

from .code_states import translate_statements_to_code_states_rows
from .io import read_xapi_json, write_csv
from .link_table import translate_statements_to_link_rows
from .main_table import translate_statements_to_main_rows
from .types import CODE_STATES_FIELDS, DATASET_METADATA_FIELDS, LINK_TABLE_FIELDS, MAIN_TABLE_FIELDS, DatasetMetadataRow


def build_arg_parser() -> argparse.ArgumentParser:
    """Construit le parser CLI du traducteur."""

    parser = argparse.ArgumentParser(
        prog="xapi_progsnap2_translator",
        description="Translate xAPI JSON (list of statements) to ProgSnap2 CSVs.",
    )
    parser.add_argument("input", help="Path to xAPI JSON file (must be a list)")
    parser.add_argument(
        "-o",
        default=str(Path("out")),
        help="Output directory, or path to MainTable.csv.",
    )
    parser.add_argument(
        "-sep",
        "--separator",
        default=",",
        help="CSV field separator to use when generating the files (default: ',').",
    )
    return parser


def resolve_output_main_path(output_path: Path) -> Path:
    """Résout un argument de sortie en chemin de `MainTable.csv`."""

    if output_path.suffix.lower() == ".csv":
        return output_path
    return output_path / "MainTable.csv"


def build_dataset_metadata_rows() -> list[DatasetMetadataRow]:
    """Construit le contenu minimal de DatasetMetadata.csv."""

    return [
        {"Property": "Version", "Value": "6"},
        {"Property": "CodeStateRepresentation", "Value": "Table"},
        {"Property": "IsEventOrderingConsistent", "Value": "true"},
        {"Property": "EventOrderScope", "Value": "Global"},
    ]


def write_dataset_metadata(output_dir: Path, delimiter: str = ",") -> Path:
    """Écrit DatasetMetadata.csv à la racine du dataset ProgSnap2."""

    metadata_path = output_dir / "DatasetMetadata.csv"
    write_csv(metadata_path, DATASET_METADATA_FIELDS, build_dataset_metadata_rows(), delimiter=delimiter)
    return metadata_path


def translate_file(
    input_path: Path,
    output_main_path: Path,
    delimiter: str = ",",
) -> tuple[Path, Path, Path]:
    """Traduit un fichier xAPI JSON et écrit les CSV ProgSnap2."""

    output_dir = output_main_path.parent
    link_table_path = output_dir / "LinkTables" / "Subject.csv"
    code_states_path = output_dir / "CodeStates" / "CodeStates.csv"

    statements = read_xapi_json(input_path)
    main_rows = translate_statements_to_main_rows(statements)
    link_rows = translate_statements_to_link_rows(statements)
    code_state_rows = translate_statements_to_code_states_rows(statements)

    write_csv(output_main_path, MAIN_TABLE_FIELDS, main_rows, delimiter=delimiter)
    write_csv(link_table_path, LINK_TABLE_FIELDS, link_rows, delimiter=delimiter)
    write_csv(code_states_path, CODE_STATES_FIELDS, code_state_rows, delimiter=delimiter)
    write_dataset_metadata(output_dir, delimiter=delimiter)
    return output_main_path, link_table_path, code_states_path


def main(argv: list[str] | None = None) -> None:
    """Point d'entrée CLI."""

    parser = build_arg_parser()
    args = parser.parse_args(argv)
    output_main_path = resolve_output_main_path(Path(args.o))
    translate_file(Path(args.input), output_main_path, delimiter=args.separator)


if __name__ == "__main__":
    main()
