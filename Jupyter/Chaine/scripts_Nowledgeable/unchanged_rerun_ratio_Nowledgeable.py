"""Calcule la proportion de soumissions consécutives au code inchangé.

Les soumissions sont triées par étudiant, ``exerciceId`` et ``answeredAt``.
Pour chaque paire consécutive d'un même exercice avec deux ``answerContent``
exploitables :

    UnchangedRerunRatio = nombre de transitions code_i == code_(i+1)
                          / nombre total de transitions comparables

Seules les fins de ligne sont harmonisées. Espaces, commentaires et indentation
restent significatifs. Les doublons portant le même ``answerUuid`` sont retirés.

Cet indicateur complète ``MaxUnchangedCodeAttempts`` : celui-ci mesure la plus
longue série, alors que le ratio décrit la fréquence globale des relances sans
modification.

Usage
-----
python unchanged_rerun_ratio_Nowledgeable.py [entree.csv] [sortie.csv]
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
COL_CODE = "answerContent"
COL_UUID = "answerUuid"
METRIC_NAME = "UnchangedRerunRatio"
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
    attempts = attempts.dropna(subset=[COL_STUDENT, COL_EXERCISE, "__timestamp"]).copy()
    if COL_UUID in attempts.columns:
        has_uuid = attempts[COL_UUID].notna() & attempts[COL_UUID].astype(str).str.strip().ne("")
        attempts = attempts.loc[~(has_uuid & attempts.duplicated(COL_UUID, keep="first"))].copy()
    return attempts.sort_values(
        [COL_STUDENT, COL_EXERCISE, "__timestamp", "__row_order"], kind="mergesort"
    ).reset_index(drop=True)


def calculate_metric(student_rows: pd.DataFrame) -> tuple[float, int, int] | None:
    unchanged = 0
    total = 0
    for _, exercise_rows in student_rows.groupby(COL_EXERCISE, sort=False):
        codes = exercise_rows["__code"].tolist()
        for code1, code2 in zip(codes, codes[1:]):
            if code1 is None or code2 is None:
                continue
            total += 1
            if code1 == code2:
                unchanged += 1
    if total == 0:
        return None
    return unchanged / total, unchanged, total


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
            out.warning("  %s : aucune paire de soumissions comparable — ignoré", sid)
            continue
        rate, unchanged, total = result
        metric_map[str(sid)] = round(rate, 6)
        out.info("  %s : %.1f %% (%d/%d transitions)", sid, rate * 100, unchanged, total)
    write_metric(metric_map, write_path)


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/session_13568_answers_corrige.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/UnchangedRerunRatio.csv"
    main(input_path, output_path)
