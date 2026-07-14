"""Calcule le ratio de tests réussis par étudiant pour les traces Nowledgeable.

Le fichier d'entrée attendu contient notamment :
- ``studentId`` : identifiant de l'étudiant ;
- ``recordedFeedback`` : objet JSON pouvant contenir une liste ``tests``.

Chaque élément de ``tests`` est compté comme un cas de test. Un test est réussi
lorsque son champ ``isRight`` vaut ``1`` ou ``True``. Les lignes sans tests
exploitables ne contribuent pas au calcul. Un étudiant sans aucun cas de test
est omis du CSV de sortie.

Usage
-----
python testratio_Nowledgeable.py [fichier_entree.csv] [fichier_sortie.csv]
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
    """Convertit ``recordedFeedback`` en dictionnaire JSON.

    Retourne ``None`` lorsque la valeur est vide, mal formée, ou ne représente
    pas un objet JSON.
    """
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


def test_is_passed(value: Any) -> bool:
    """Indique si une valeur ``isRight`` représente un test réussi."""
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true"}
    return False


def calculate_test_pass_rate(student_rows: pd.DataFrame) -> tuple[float, int, int] | None:
    """Calcule le taux de réussite des cas de test d'un étudiant.

    Retourne ``(ratio, tests_reussis, tests_total)`` ou ``None`` si aucun cas
    de test détaillé n'est disponible pour cet étudiant.
    """
    total_tests = 0
    passed_tests = 0

    for raw_feedback in student_rows[COL_FEEDBACK]:
        feedback = parse_feedback(raw_feedback)
        if feedback is None:
            continue

        tests = feedback.get("tests")
        if not isinstance(tests, list):
            continue

        for test in tests:
            if not isinstance(test, dict):
                continue
            total_tests += 1
            if test_is_passed(test.get("isRight")):
                passed_tests += 1

    if total_tests == 0:
        return None

    return passed_tests / total_tests, passed_tests, total_tests


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


def write_metric(name: str, metric_map: dict[str, float], path: str) -> None:
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

    metric_map: dict[str, float] = {}
    dropped = 0

    for student_id in sorted(students):
        student_rows = df[df[COL_STUDENT] == student_id]
        result = calculate_test_pass_rate(student_rows)

        if result is None:
            out.warning("  %s : aucun cas de test détaillé — ignoré", student_id)
            dropped += 1
            continue

        rate, passed_tests, total_tests = result
        metric_map[str(student_id)] = round(rate, 6)
        out.info(
            "  %s : %.1f %% (%d/%d tests)",
            student_id,
            rate * 100,
            passed_tests,
            total_tests,
        )

    out.info("%d étudiant(s) ignoré(s) (aucun test détaillé)", dropped)
    write_metric("TestPassRate", metric_map, write_path)


if __name__ == "__main__":
    input_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/session_13568_answers_corrige.csv"
    )
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/TestPassRate.csv"
    main(input_path, output_path)
