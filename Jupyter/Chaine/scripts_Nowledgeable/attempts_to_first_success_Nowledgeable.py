"""Calcule le nombre moyen de tentatives jusqu'au premier succès.

L'unité est ``exerciceId``. Les soumissions sont triées par ``answeredAt`` et
les doublons de collecte identifiés par ``answerUuid`` sont retirés.
Une soumission est réussie lorsque ``answerIsRight`` vaut 1/True.

Pour chaque exercice qui atteint finalement un succès :

    attempts_to_success = rang de la première soumission réussie (1, 2, ...)

La métrique étudiant est la moyenne de ces rangs. Les exercices jamais réussis
sont exclus, car le nombre de tentatives "jusqu'au succès" y est censuré.

Usage
-----
python attempts_to_first_success_Nowledgeable.py [entree.csv] [sortie.csv]
"""

from __future__ import annotations

import csv
import logging
import pathlib
import sys
from typing import Any

import pandas as pd

logging.basicConfig(format="%(asctime)s [%(levelname)-5.5s]  %(message)s", level=logging.INFO)
out = logging.getLogger()

COL_STUDENT = "studentId"
COL_EXERCISE = "exerciceId"
COL_TIMESTAMP = "answeredAt"
COL_RIGHT = "answerIsRight"
COL_UUID = "answerUuid"
METRIC_NAME = "AttemptsToFirstSuccess"
REQUIRED_COLS = [COL_STUDENT, COL_EXERCISE, COL_TIMESTAMP, COL_RIGHT]


def parse_timestamps(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns, UTC]")
    numeric_mask = numeric.notna()
    ms = numeric_mask & (numeric.abs() >= 100_000_000_000)
    sec = numeric_mask & ~ms
    if sec.any():
        parsed.loc[sec] = pd.to_datetime(numeric.loc[sec], unit="s", errors="coerce", utc=True)
    if ms.any():
        parsed.loc[ms] = pd.to_datetime(numeric.loc[ms], unit="ms", errors="coerce", utc=True)
    text = ~numeric_mask & series.notna()
    if text.any():
        parsed.loc[text] = pd.to_datetime(series.loc[text], errors="coerce", utc=True)
    return parsed


def is_success(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool) and not pd.isna(value):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true"}
    return False


def prepare_attempts(df: pd.DataFrame) -> pd.DataFrame:
    attempts = df.copy()
    attempts[COL_STUDENT] = attempts[COL_STUDENT].astype("string")
    attempts["__row_order"] = range(len(attempts))
    attempts["__timestamp"] = parse_timestamps(attempts[COL_TIMESTAMP])
    attempts["__success"] = attempts[COL_RIGHT].apply(is_success)
    attempts = attempts.dropna(subset=[COL_STUDENT, COL_EXERCISE, "__timestamp"]).copy()

    if COL_UUID in attempts.columns:
        has_uuid = attempts[COL_UUID].notna() & attempts[COL_UUID].astype(str).str.strip().ne("")
        duplicate = has_uuid & attempts.duplicated(subset=[COL_UUID], keep="first")
        if duplicate.any():
            out.info("%d soumission(s) dupliquée(s) retirée(s)", int(duplicate.sum()))
            attempts = attempts.loc[~duplicate].copy()

    return attempts.sort_values(
        [COL_STUDENT, COL_EXERCISE, "__timestamp", "__row_order"], kind="mergesort"
    ).reset_index(drop=True)


def calculate_metric(student_rows: pd.DataFrame) -> tuple[float, int] | None:
    values: list[int] = []
    for _, exercise_rows in student_rows.groupby(COL_EXERCISE, sort=False):
        successes = exercise_rows["__success"].tolist()
        try:
            first_success_index = successes.index(True)
        except ValueError:
            continue
        values.append(first_success_index + 1)
    if not values:
        return None
    return sum(values) / len(values), len(values)


def load_csv(path: str) -> pd.DataFrame:
    out.info("Chargement de %s …", path)
    df = pd.read_csv(path, dtype={COL_STUDENT: "string"}, on_bad_lines="skip", engine="python")
    out.info("  %d lignes, %d colonnes", len(df), len(df.columns))
    return df


def check_columns(df: pd.DataFrame) -> bool:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        out.error("Colonnes manquantes : %s", missing)
        return False
    return True


def write_metric(metric_map: dict[str, float], path: str) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["SubjectID", METRIC_NAME], lineterminator="\n")
        writer.writeheader()
        for sid, value in sorted(metric_map.items()):
            writer.writerow({"SubjectID": sid, METRIC_NAME: value})
    out.info("Résultat écrit dans %s (%d étudiants)", path, len(metric_map))


def main(read_path: str, write_path: str) -> None:
    df = load_csv(read_path)
    if not check_columns(df):
        sys.exit(1)
    attempts = prepare_attempts(df)
    students = attempts[COL_STUDENT].dropna().unique().tolist()
    metric_map: dict[str, float] = {}
    dropped = 0
    for sid in sorted(students):
        result = calculate_metric(attempts[attempts[COL_STUDENT] == sid])
        if result is None:
            out.warning("  %s : aucun exercice réussi — ignoré", sid)
            dropped += 1
            continue
        value, exercises = result
        metric_map[str(sid)] = round(value, 6)
        out.info("  %s : %.3f tentative(s) (%d exercice(s) réussi(s))", sid, value, exercises)
    out.info("%d étudiant(s) ignoré(s)", dropped)
    write_metric(metric_map, write_path)


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/session_13568_answers_corrige.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/AttemptsToFirstSuccess.csv"
    main(input_path, output_path)
