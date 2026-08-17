"""Calcule le nombre total de cas de test exécutés par étudiant.

Le fichier d'entrée Nowledgeable doit contenir au minimum :
- ``studentId`` : identifiant de l'étudiant ;
- ``recordedFeedback`` : objet JSON pouvant contenir une liste ``tests``.

Chaque dictionnaire présent dans ``recordedFeedback["tests"]`` compte comme un
cas de test exécuté. Un même test réexécuté lors de plusieurs soumissions est
compté à chaque exécution. Ce calcul correspond au dénominateur utilisé par
``test_pass_rate_Nowledgeable.py``.

Les étudiants pour lesquels aucun cas de test détaillé n'est trouvé reçoivent
la valeur 0.

Usage
-----
python total_test_count_Nowledgeable.py [fichier_entree.csv] [fichier_sortie.csv]
"""

import csv
import json
import logging
import pathlib
import sys
from typing import Any

import pandas as pd


logging.basicConfig(
    format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
    level=logging.INFO,
)
out = logging.getLogger()

COL_STUDENT = "studentId"
COL_FEEDBACK = "recordedFeedback"
REQUIRED_COLS = [COL_STUDENT, COL_FEEDBACK]


def parse_feedback(raw: Any) -> dict[str, Any] | None:
    """Convertit ``recordedFeedback`` en dictionnaire JSON exploitable."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw.strip():
        return None

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        out.debug("JSON recordedFeedback invalide : %s", raw[:120])
        return None

    return parsed if isinstance(parsed, dict) else None


def calculate_total_test_count(student_rows: pd.DataFrame) -> int:
    """Compte les cas de test détaillés présents dans les lignes d'un étudiant."""
    total_tests = 0

    for raw_feedback in student_rows[COL_FEEDBACK]:
        feedback = parse_feedback(raw_feedback)
        if feedback is None:
            continue

        tests = feedback.get("tests")
        if not isinstance(tests, list):
            continue

        # Même convention que test_pass_rate_Nowledgeable.py : seuls les éléments
        # structurés sous forme de dictionnaire sont des cas de test valides.
        total_tests += sum(isinstance(test, dict) for test in tests)

    return total_tests


def load_csv(path: str) -> pd.DataFrame:
    out.info("Chargement de %s …", path)
    df = pd.read_csv(
        path,
        dtype={COL_STUDENT: "string"},
        on_bad_lines="skip",
        engine="python",
    )
    out.info("  %d lignes, %d colonnes", len(df), len(df.columns))
    return df


def check_columns(df: pd.DataFrame, required: list[str]) -> bool:
    missing = [column for column in required if column not in df.columns]
    if missing:
        out.error("Colonnes manquantes dans le CSV : %s", missing)
        return False
    return True


def write_metric(name: str, metric_map: dict[str, int], path: str) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["SubjectID", name],
            lineterminator="\n",
        )
        writer.writeheader()

        for subject_id, value in sorted(metric_map.items(), key=lambda item: item[0]):
            writer.writerow({"SubjectID": subject_id, name: value})

    out.info("Résultat écrit dans %s (%d étudiants)", path, len(metric_map))


def main(read_path: str, write_path: str) -> None:
    df = load_csv(read_path)

    if not check_columns(df, REQUIRED_COLS):
        sys.exit(1)

    students = df[COL_STUDENT].dropna().unique().tolist()
    out.info("%d étudiant(s) trouvé(s)", len(students))

    metric_map: dict[str, int] = {}

    for student_id in sorted(students):
        student_rows = df[df[COL_STUDENT] == student_id]
        total_tests = calculate_total_test_count(student_rows)
        metric_map[str(student_id)] = total_tests
        out.info("  %s : %d test(s)", student_id, total_tests)

    write_metric("TotalTestCount", metric_map, write_path)


if __name__ == "__main__":
    input_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/session_13568_answers_corrige.csv"
    )
    output_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "out/TotalTestCount.csv"
    )
    main(input_path, output_path)
