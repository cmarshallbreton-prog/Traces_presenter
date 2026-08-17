"""Calcule l'amplitude moyenne des changements de code dans Nowledgeable.

Les soumissions sont comparées consécutivement à l'intérieur du même exercice.
Pour chaque transition où les deux ``answerContent`` sont disponibles et
DIFFÉRENTS, la dissimilarité est :

    d(c1, c2) = 1 - SequenceMatcher(c1, c2).ratio()
              = 1 - 2*M / (len(c1) + len(c2))

M est le nombre de caractères appartenant aux blocs correspondants trouvés par
``difflib.SequenceMatcher``. La valeur est bornée dans [0, 1].

La métrique étudiant est la moyenne de ``d`` sur les transitions avec
changement. Les codes identiques sont exclus afin de ne pas dupliquer
``UnchangedRerunRatio``.

Usage
-----
python code_change_magnitude_Nowledgeable.py [entree.csv] [sortie.csv]
"""

from __future__ import annotations

import csv
import difflib
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
COL_CODE = "answerContent"
COL_UUID = "answerUuid"
METRIC_NAME = "CodeChangeMagnitude"
REQUIRED_COLS = [COL_STUDENT, COL_EXERCISE, COL_TIMESTAMP, COL_CODE]


def parse_timestamps(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns, UTC]")
    mask = numeric.notna()
    ms = mask & (numeric.abs() >= 100_000_000_000)
    sec = mask & ~ms
    if sec.any():
        parsed.loc[sec] = pd.to_datetime(numeric.loc[sec], unit="s", errors="coerce", utc=True)
    if ms.any():
        parsed.loc[ms] = pd.to_datetime(numeric.loc[ms], unit="ms", errors="coerce", utc=True)
    text = ~mask & series.notna()
    if text.any():
        parsed.loc[text] = pd.to_datetime(series.loc[text], errors="coerce", utc=True)
    return parsed


def normalize_code(value: Any) -> str | None:
    if pd.isna(value):
        return None
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def prepare_attempts(df: pd.DataFrame) -> pd.DataFrame:
    attempts = df.copy()
    attempts[COL_STUDENT] = attempts[COL_STUDENT].astype("string")
    attempts["__row_order"] = range(len(attempts))
    attempts["__timestamp"] = parse_timestamps(attempts[COL_TIMESTAMP])
    attempts["__code"] = attempts[COL_CODE].apply(normalize_code)
    attempts = attempts.dropna(subset=[COL_STUDENT, COL_EXERCISE, "__timestamp", "__code"]).copy()
    if COL_UUID in attempts.columns:
        has_uuid = attempts[COL_UUID].notna() & attempts[COL_UUID].astype(str).str.strip().ne("")
        attempts = attempts.loc[~(has_uuid & attempts.duplicated(COL_UUID, keep="first"))].copy()
    return attempts.sort_values(
        [COL_STUDENT, COL_EXERCISE, "__timestamp", "__row_order"], kind="mergesort"
    ).reset_index(drop=True)


def code_distance(code1: str, code2: str) -> float:
    if code1 == code2:
        return 0.0
    return min(max(1.0 - difflib.SequenceMatcher(None, code1, code2).ratio(), 0.0), 1.0)


def calculate_metric(student_rows: pd.DataFrame) -> tuple[float, int] | None:
    distances: list[float] = []
    for _, exercise_rows in student_rows.groupby(COL_EXERCISE, sort=False):
        codes = exercise_rows["__code"].tolist()
        for code1, code2 in zip(codes, codes[1:]):
            if code1 == code2:
                continue
            distances.append(code_distance(code1, code2))
    if not distances:
        return None
    return sum(distances) / len(distances), len(distances)


def write_metric(metric_map: dict[str, float], path: str) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["SubjectID", METRIC_NAME], lineterminator="\n")
        writer.writeheader()
        for sid, value in sorted(metric_map.items()):
            writer.writerow({"SubjectID": sid, METRIC_NAME: value})


def main(read_path: str, write_path: str) -> None:
    df = pd.read_csv(read_path, dtype={COL_STUDENT: "string"}, on_bad_lines="skip", engine="python")
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        out.error("Colonnes manquantes : %s", missing)
        sys.exit(1)
    attempts = prepare_attempts(df)
    metric_map: dict[str, float] = {}
    for sid in sorted(attempts[COL_STUDENT].dropna().unique().tolist()):
        result = calculate_metric(attempts[attempts[COL_STUDENT] == sid])
        if result is None:
            out.warning("  %s : aucun changement de code observable — ignoré", sid)
            continue
        value, transitions = result
        metric_map[str(sid)] = round(value, 6)
        out.info("  %s : %.4f (%d transition(s))", sid, value, transitions)
    write_metric(metric_map, write_path)


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/session_13568_answers_corrige.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/CodeChangeMagnitude.csv"
    main(input_path, output_path)
