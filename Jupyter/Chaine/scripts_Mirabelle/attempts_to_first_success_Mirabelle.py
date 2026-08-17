"""Calcule le nombre moyen de tentatives jusqu'au premier succès dans Mirabelle.

L'unité d'analyse est une fonction testée dans un fichier et une session.
Chaque événement ``Run.Test`` contenant au moins un cas pour cette fonction
constitue une tentative. Une tentative est réussie si TOUS les cas de test de
la fonction présents dans ce Run.Test ont ``status`` réussi.

Pour chaque unité qui atteint finalement un succès :

    attempts_to_success = rang de la première tentative réussie (1, 2, ...)

La métrique étudiant est la moyenne de ces rangs. Les unités qui ne réussissent
jamais sont exclues car leur "temps jusqu'au succès" est censuré/inconnu.

Usage
-----
python attempts_to_first_success_Mirabelle.py [entree.csv] [sortie.csv]
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any

import pandas as pd

import utils_Mirabelle as um

out = um.out

COL_EVENT_ID = "_id.$oid"
FUNCTION_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:\(|$)")
METRIC_NAME = "AttemptsToFirstSuccess"
REQUIRED_COLS = [
    um.COL_ACTOR,
    um.COL_VERB,
    um.COL_TESTS,
    um.COL_TS,
]


def status_is_passed(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool) and not pd.isna(value):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "passed", "pass"}
    return False


def extract_function_name(case: dict[str, Any]) -> str | None:
    for key in ("name", "tested_line"):
        raw = case.get(key)
        if isinstance(raw, str) and raw.strip():
            match = FUNCTION_RE.match(raw)
            if match:
                return match.group(1)
    return None


def extract_filename(case: dict[str, Any], fallback: Any) -> str:
    raw = case.get("filename")
    if isinstance(raw, str) and raw.strip():
        return os.path.basename(raw.strip())
    if pd.notna(fallback) and str(fallback).strip():
        return os.path.basename(str(fallback).strip())
    return "<fichier_inconnu>"


def prepare_function_attempts(df: pd.DataFrame) -> pd.DataFrame:
    """Construit une ligne par Run.Test et fonction observée."""
    rows = df[df[um.COL_VERB] == um.VERB_TEST].copy()
    rows["__row_order"] = range(len(rows))
    rows["__timestamp"] = pd.to_datetime(rows[um.COL_TS], errors="coerce", utc=True)
    rows = rows.dropna(subset=[um.COL_ACTOR, "__timestamp"])
    rows = um.add_activity_session_ids(rows, timestamp_col="__timestamp")

    if COL_EVENT_ID in rows.columns:
        has_id = rows[COL_EVENT_ID].notna() & rows[COL_EVENT_ID].astype(str).str.strip().ne("")
        duplicate = has_id & rows.duplicated(subset=[COL_EVENT_ID], keep="first")
        rows = rows.loc[~duplicate].copy()

    records: list[dict[str, Any]] = []
    for _, row in rows.iterrows():
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for case in um.parse_tests(row[um.COL_TESTS]):
            if not isinstance(case, dict):
                continue
            function = extract_function_name(case)
            if function is None:
                continue
            filename = extract_filename(case, row.get(um.COL_FILE))
            grouped.setdefault((filename, function), []).append(case)

        for (filename, function), cases in grouped.items():
            valid = [case for case in cases if "status" in case]
            if not valid:
                continue
            records.append({
                um.COL_ACTOR: str(row[um.COL_ACTOR]),
                "__session": str(row[um.COL_ACTIVITY_SESSION]),
                "__filename": filename,
                "__function": function,
                "__timestamp": row["__timestamp"],
                "__row_order": row["__row_order"],
                "__success": all(status_is_passed(case.get("status")) for case in valid),
            })

    columns = [
        um.COL_ACTOR, "__session", "__filename", "__function",
        "__timestamp", "__row_order", "__success",
    ]
    attempts = pd.DataFrame.from_records(records, columns=columns)
    if attempts.empty:
        return attempts
    return attempts.sort_values(
        [um.COL_ACTOR, "__session", "__filename", "__function", "__timestamp", "__row_order"],
        kind="mergesort",
    ).reset_index(drop=True)


def calculate_metric(actor_rows: pd.DataFrame) -> tuple[float, int] | None:
    values: list[int] = []
    group_cols = ["__session", "__filename", "__function"]

    for _, unit_rows in actor_rows.groupby(group_cols, sort=False):
        successes = unit_rows["__success"].tolist()
        try:
            first_success_index = successes.index(True)
        except ValueError:
            continue
        values.append(first_success_index + 1)

    if not values:
        return None
    return sum(values) / len(values), len(values)


def main(read_path: str, write_path: str) -> None:
    df = um.load_csv(read_path)
    if not um.check_columns(df, REQUIRED_COLS):
        sys.exit(1)

    attempts = prepare_function_attempts(df)
    actors = df[um.COL_ACTOR].dropna().astype(str).unique().tolist()
    metric_map: dict[str, float] = {}
    dropped = 0

    for actor in sorted(actors):
        actor_rows = attempts[attempts[um.COL_ACTOR] == actor] if not attempts.empty else attempts
        result = calculate_metric(actor_rows)
        if result is None:
            out.warning("  %s : aucune fonction avec succès observable — ignoré", actor)
            dropped += 1
            continue
        value, units = result
        metric_map[actor] = round(value, 6)
        out.info("  %s : %.3f tentative(s) (%d unité(s) réussie(s))", actor, value, units)

    out.info("%d étudiant(s) ignoré(s)", dropped)
    um.write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/traces_20_sept_10_11.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/AttemptsToFirstSuccess.csv"
    main(input_path, output_path)
