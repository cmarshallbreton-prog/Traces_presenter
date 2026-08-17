"""Calcule la proportion de relances de tests sans changement de code.

Les ``Run.Test`` sont comparés consécutivement à l'intérieur du même fichier et
de la même session d’activité (pause > 5 min). Une transition est exploitable si les deux
``P_codeState`` sont présents. Après harmonisation des fins de ligne :

    UnchangedRerunRatio = transitions où code_i == code_(i+1)
                          / transitions avec deux codes exploitables

Aucun nettoyage des espaces, commentaires ou indentation n'est effectué : ces
modifications sont considérées comme de vrais changements de code.

Usage
-----
python unchanged_rerun_ratio_Mirabelle.py [entree.csv] [sortie.csv]
"""

from __future__ import annotations

import os
import sys
from typing import Any

import pandas as pd

import utils_Mirabelle as um

out = um.out
COL_EVENT_ID = "_id.$oid"
METRIC_NAME = "UnchangedRerunRatio"
REQUIRED_COLS = [
    um.COL_ACTOR,
    um.COL_VERB,
    um.COL_TS,
    um.COL_CODESTATE,
    um.COL_TESTS,
]


def normalize_code(value: Any) -> str | None:
    if pd.isna(value):
        return None
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def infer_filename(row: pd.Series) -> str | None:
    fallback = row.get(um.COL_FILE)
    if pd.notna(fallback) and str(fallback).strip():
        return os.path.basename(str(fallback).strip())
    for case in um.parse_tests(row.get(um.COL_TESTS)):
        if isinstance(case, dict):
            raw = case.get("filename")
            if isinstance(raw, str) and raw.strip():
                return os.path.basename(raw.strip())
    return None


def prepare_attempts(df: pd.DataFrame) -> pd.DataFrame:
    rows = df[df[um.COL_VERB] == um.VERB_TEST].copy()
    rows["__row_order"] = range(len(rows))
    rows["__timestamp"] = pd.to_datetime(rows[um.COL_TS], errors="coerce", utc=True)
    rows["__code"] = rows[um.COL_CODESTATE].apply(normalize_code)
    rows["__filename"] = rows.apply(infer_filename, axis=1)
    rows = rows.dropna(
        subset=[um.COL_ACTOR, "__timestamp", "__code", "__filename"]
).copy()
    rows = um.add_activity_session_ids(rows, timestamp_col="__timestamp")

    if COL_EVENT_ID in rows.columns:
        has_id = rows[COL_EVENT_ID].notna() & rows[COL_EVENT_ID].astype(str).str.strip().ne("")
        rows = rows.loc[~(has_id & rows.duplicated(COL_EVENT_ID, keep="first"))].copy()

    rows[um.COL_ACTOR] = rows[um.COL_ACTOR].astype(str)
    rows["__session"] = rows[um.COL_ACTIVITY_SESSION].astype(str)
    return rows.sort_values(
        [um.COL_ACTOR, "__session", "__filename", "__timestamp", "__row_order"],
        kind="mergesort",
    ).reset_index(drop=True)


def calculate_metric(actor_rows: pd.DataFrame) -> tuple[float, int, int] | None:
    total = 0
    unchanged = 0

    for _, unit_rows in actor_rows.groupby(["__session", "__filename"], sort=False):
        codes = unit_rows["__code"].tolist()
        for code1, code2 in zip(codes, codes[1:]):
            total += 1
            if code1 == code2:
                unchanged += 1

    if total == 0:
        return None
    return unchanged / total, unchanged, total


def main(read_path: str, write_path: str) -> None:
    df = um.load_csv(read_path)
    if not um.check_columns(df, REQUIRED_COLS):
        sys.exit(1)

    attempts = prepare_attempts(df)
    actors = df[um.COL_ACTOR].dropna().astype(str).unique().tolist()
    metric_map: dict[str, float] = {}
    dropped = 0

    for actor in sorted(actors):
        result = calculate_metric(attempts[attempts[um.COL_ACTOR] == actor])
        if result is None:
            out.warning("  %s : aucune paire de Run.Test comparable — ignoré", actor)
            dropped += 1
            continue
        rate, unchanged, total = result
        metric_map[actor] = round(rate, 6)
        out.info("  %s : %.1f %% (%d/%d relances)", actor, rate * 100, unchanged, total)

    out.info("%d étudiant(s) ignoré(s)", dropped)
    um.write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/traces_20_sept_10_11.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/UnchangedRerunRatio.csv"
    main(input_path, output_path)
