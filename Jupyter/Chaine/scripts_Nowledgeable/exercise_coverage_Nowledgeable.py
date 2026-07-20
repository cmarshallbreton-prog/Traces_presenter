"""Calcule le nombre d'exercices traités par étudiant.

Un exercice est considéré comme traité par un étudiant si au moins une des
conditions suivantes est remplie :

- le meilleur ``answerScore`` obtenu sur cet exercice est strictement supérieur
  à 0 ;
- au moins deux versions distinctes de ``answerContent`` ont été soumises pour
  cet exercice.

Les soumissions dupliquées portant le même ``answerUuid`` sont retirées avant
le calcul. Pour comparer les versions de code, seules les fins de ligne sont
harmonisées (CRLF/CR vers LF). Toute autre modification, y compris un changement
d'espaces, de commentaires ou d'indentation, constitue une nouvelle version.
Les valeurs ``answerContent`` manquantes ne sont pas comptées comme des versions
de code.

La sortie contient une ligne par étudiant, y compris pour les étudiants qui
n'ont traité aucun exercice.

Usage
-----
python exercise_coverage_Nowledgeable.py \\
    [fichier_entree.csv] [fichier_sortie.csv]
"""

from __future__ import annotations

import csv
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
COL_EXERCISE = "exerciceId"
COL_SCORE = "answerScore"
COL_CODE = "answerContent"
COL_ANSWER_UUID = "answerUuid"

REQUIRED_COLS = [COL_STUDENT, COL_EXERCISE, COL_SCORE, COL_CODE]
METRIC_NAME = "ExerciseCoverage"


def normalize_code(value: Any) -> str | None:
    """Retourne une version comparable du code, ou ``None`` s'il est absent.

    Les fins de ligne sont harmonisées afin qu'un passage de CRLF à LF ne soit
    pas interprété comme une nouvelle version. Les autres caractères sont
    conservés tels quels.
    """
    if pd.isna(value):
        return None
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def prepare_attempts(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie, déduplique et annote les soumissions exploitables."""
    attempts = df.copy()
    attempts[COL_STUDENT] = attempts[COL_STUDENT].astype("string")
    attempts["__score"] = pd.to_numeric(attempts[COL_SCORE], errors="coerce")
    attempts["__code"] = attempts[COL_CODE].apply(normalize_code)

    invalid_scores = int(attempts["__score"].isna().sum())
    if invalid_scores:
        out.warning(
            "%d ligne(s) avec answerScore absent ou invalide : "
            "elles ne valideront pas le critère de score",
            invalid_scores,
        )

    missing_codes = int(attempts["__code"].isna().sum())
    if missing_codes:
        out.warning(
            "%d ligne(s) sans answerContent : "
            "elles ne compteront pas comme version de code",
            missing_codes,
        )

    attempts = attempts.dropna(subset=[COL_STUDENT, COL_EXERCISE]).copy()

    if COL_ANSWER_UUID in attempts.columns:
        has_uuid = attempts[COL_ANSWER_UUID].notna() & (
            attempts[COL_ANSWER_UUID].astype(str).str.strip() != ""
        )
        duplicated_uuid = has_uuid & attempts.duplicated(
            subset=[COL_ANSWER_UUID], keep="first"
        )
        duplicate_count = int(duplicated_uuid.sum())
        if duplicate_count:
            out.info(
                "%d soumission(s) dupliquée(s) par answerUuid ont été retirées",
                duplicate_count,
            )
            attempts = attempts.loc[~duplicated_uuid].copy()

    return attempts.reset_index(drop=True)


def calculate_exercise_coverage(
    student_rows: pd.DataFrame,
) -> tuple[int, int, int]:
    """Compte les exercices traités par un étudiant.

    Retourne un triplet :

    ``(nombre_total, traites_par_score, traites_par_versions_uniquement)``.

    La troisième valeur compte les exercices qui ne satisfont pas le critère
    de score, mais satisfont celui des deux versions distinctes. Elle sert au
    journal d'exécution et évite le double comptage dans le total.
    """
    treated_count = 0
    treated_by_score = 0
    treated_by_versions_only = 0

    for _, exercise_rows in student_rows.groupby(COL_EXERCISE, sort=False):
        best_score = exercise_rows["__score"].max(skipna=True)
        has_positive_score = pd.notna(best_score) and best_score > 0

        distinct_code_count = exercise_rows["__code"].dropna().nunique()
        has_two_distinct_versions = distinct_code_count >= 2

        if has_positive_score or has_two_distinct_versions:
            treated_count += 1

            if has_positive_score:
                treated_by_score += 1
            else:
                treated_by_versions_only += 1

    return treated_count, treated_by_score, treated_by_versions_only


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

    # On récupère les étudiants avant le nettoyage pour conserver dans la sortie
    # ceux dont aucune ligne ne serait finalement exploitable.
    students = df[COL_STUDENT].astype("string").dropna().unique().tolist()
    attempts = prepare_attempts(df)

    out.info("%d étudiant(s) trouvé(s)", len(students))

    metric_map: dict[str, int] = {}

    for student_id in sorted(students):
        student_rows = attempts[attempts[COL_STUDENT] == student_id]
        coverage, by_score, by_versions_only = calculate_exercise_coverage(
            student_rows
        )

        metric_map[str(student_id)] = coverage
        out.info(
            "  %s : %d exercice(s) traité(s) "
            "(%d avec score > 0, %d par versions distinctes uniquement)",
            student_id,
            coverage,
            by_score,
            by_versions_only,
        )

    write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    input_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/session_13568_answers_corrige.csv"
    )
    output_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "out/ExerciseCoverage.csv"
    )
    main(input_path, output_path)
