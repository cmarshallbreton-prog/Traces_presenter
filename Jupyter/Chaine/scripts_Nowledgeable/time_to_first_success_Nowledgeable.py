"""Calcule le temps moyen jusqu'au premier succès par étudiant.

L'unité est ``exerciceId``. Pour chaque exercice finalement réussi :

    time_to_success = answeredAt(premier succès) - answeredAt(première tentative)

Le temps est exprimé en minutes et la métrique étudiant est la moyenne des
durées sur les exercices réussis. Les exercices jamais réussis sont exclus.
Les doublons portant le même ``answerUuid`` sont retirés.

Usage
-----
python time_to_first_success_Nowledgeable.py [entree.csv] [sortie.csv]
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
METRIC_NAME = "TimeToFirstSuccess"
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
        duplicate = has_uuid & attempts.duplicated(COL_UUID, keep="first")
        attempts = attempts.loc[~duplicate].copy()
    return attempts.sort_values(
        [COL_STUDENT, COL_EXERCISE, "__timestamp", "__row_order"], kind="mergesort"
    ).reset_index(drop=True)


def calculate_metric(student_rows: pd.DataFrame) -> tuple[float, int] | None:
    durations: list[float] = []
    for _, exercise_rows in student_rows.groupby(COL_EXERCISE, sort=False):
        successful = exercise_rows[exercise_rows["__success"]]
        if successful.empty:
            continue
        first_ts = exercise_rows.iloc[0]["__timestamp"]
        success_ts = successful.iloc[0]["__timestamp"]
        durations.append(max((success_ts - first_ts).total_seconds() / 60.0, 0.0))
    if not durations:
        return None
    return sum(durations) / len(durations), len(durations)


def load_csv(path: str) -> pd.DataFrame:
    out.info("Chargement de %s …", path)
    return pd.read_csv(path, dtype={COL_STUDENT: "string"}, on_bad_lines="skip", engine="python")


def write_metric(metric_map: dict[str, float], path: str) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["SubjectID", METRIC_NAME], lineterminator="\n")
        writer.writeheader()
        for sid, value in sorted(metric_map.items()):
            writer.writerow({"SubjectID": sid, METRIC_NAME: value})


def main(read_path: str, write_path: str) -> None:
    df = load_csv(read_path)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        out.error("Colonnes manquantes : %s", missing)
        sys.exit(1)
    attempts = prepare_attempts(df)
    metric_map: dict[str, float] = {}
    for sid in sorted(attempts[COL_STUDENT].dropna().unique().tolist()):
        result = calculate_metric(attempts[attempts[COL_STUDENT] == sid])
        if result is None:
            out.warning("  %s : aucun temps jusqu'au succès mesurable — ignoré", sid)
            continue
        value, exercises = result
        metric_map[str(sid)] = round(value, 6)
        out.info("  %s : %.3f min (%d exercice(s))", sid, value, exercises)
    write_metric(metric_map, write_path)


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/session_13568_answers_corrige.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/TimeToFirstSuccess.csv"
    main(input_path, output_path)
