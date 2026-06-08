import csv
import json
from pathlib import Path

from .types import Statement


def read_xapi_json(path: Path) -> list[Statement]:
    """Lit un fichier JSON contenant une liste de statements xAPI."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Expected xAPI JSON to be a list of statements")

    statements: list[Statement] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Statement #{index} is not an object")
        statements.append(item)

    return statements


def write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
    delimiter: str = ",",
) -> None:
    """Écrit un CSV avec en-têtes explicites."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            delimiter=delimiter,
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(rows)
