"""Calcule le taux de succès dès la première tentative dans Mirabelle.

L'unité est une fonction testée dans un fichier et une session. La première
apparition chronologique de cette fonction dans un ``Run.Test`` constitue sa
première tentative. Elle est réussie si tous les cas de test de cette fonction
présents dans le Run.Test ont un ``status`` réussi.

    FirstAttemptSuccessRate = unités réussies au 1er essai / unités observées

Usage
-----
python first_attempt_success_rate_Mirabelle.py [entree.csv] [sortie.csv]
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
METRIC_NAME = "FirstAttemptSuccessRate"
REQUIRED_COLS = [um.COL_ACTOR, um.COL_VERB, um.COL_TESTS, um.COL_TS]


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
    rows = df[df[um.COL_VERB] == um.VERB_TEST].copy()
    rows["__row_order"] = range(len(rows))
    rows["__timestamp"] = pd.to_datetime(rows[um.COL_TS], errors="coerce", utc=True)
    rows = rows.dropna(subset=[um.COL_ACTOR, "__timestamp"])
    rows = um.add_activity_session_ids(rows, timestamp_col="__timestamp")

    if COL_EVENT_ID in rows.columns:
        has_id = rows[COL_EVENT_ID].notna() & rows[COL_EVENT_ID].astype(str).str.strip().ne("")
        rows = rows.loc[~(has_id & rows.duplicated(COL_EVENT_ID, keep="first"))].copy()

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


def calculate_metric(actor_rows: pd.DataFrame) -> tuple[float, int, int] | None:
    total = 0
    first_successes = 0
    group_cols = ["__session", "__filename", "__function"]

    for _, unit_rows in actor_rows.groupby(group_cols, sort=False):
        if unit_rows.empty:
            continue
        total += 1
        if bool(unit_rows.iloc[0]["__success"]):
            first_successes += 1

    if total == 0:
        return None
    return first_successes / total, first_successes, total


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
            out.warning("  %s : aucune unité testée — ignoré", actor)
            dropped += 1
            continue
        rate, successes, total = result
        metric_map[actor] = round(rate, 6)
        out.info("  %s : %.1f %% (%d/%d unités)", actor, rate * 100, successes, total)

    out.info("%d étudiant(s) ignoré(s)", dropped)
    um.write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/traces_20_sept_10_11.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/FirstAttemptSuccessRate.csv"
    main(input_path, output_path)
