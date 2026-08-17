"""Calcule l'amplitude moyenne des changements de code dans Mirabelle.

Les ``Run.Test`` sont ordonnés à l'intérieur de chaque couple
``(session d’activité, fichier)``. Pour chaque paire consécutive avec deux
``P_codeState`` disponibles et différents, on calcule une dissimilarité de
séquence à l'aide de ``difflib.SequenceMatcher`` :

    d(c1, c2) = 1 - 2*M / (len(c1) + len(c2))

M est le nombre total de caractères appartenant aux blocs correspondants
trouvés par SequenceMatcher. ``d`` est dans [0, 1] : 0 signifie identique et
une valeur élevée indique une modification importante. Les transitions sans
changement sont exclues de cette métrique et sont décrites séparément par
``UnchangedRerunRatio``.

La métrique étudiant est la moyenne de ``d`` sur ses transitions avec
changement de code.

Usage
-----
python code_change_magnitude_Mirabelle.py [entree.csv] [sortie.csv]
"""

from __future__ import annotations

import difflib
import os
import sys
from typing import Any

import pandas as pd

import utils_Mirabelle as um

out = um.out
COL_EVENT_ID = "_id.$oid"
METRIC_NAME = "CodeChangeMagnitude"
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


def code_distance(code1: str, code2: str) -> float:
    """Dissimilarité normalisée dérivée du ratio de SequenceMatcher."""
    if code1 == code2:
        return 0.0
    ratio = difflib.SequenceMatcher(None, code1, code2).ratio()
    return min(max(1.0 - ratio, 0.0), 1.0)


def calculate_metric(actor_rows: pd.DataFrame) -> tuple[float, int] | None:
    distances: list[float] = []

    for _, unit_rows in actor_rows.groupby(["__session", "__filename"], sort=False):
        codes = unit_rows["__code"].tolist()
        for code1, code2 in zip(codes, codes[1:]):
            if code1 == code2:
                continue
            distances.append(code_distance(code1, code2))

    if not distances:
        return None
    return sum(distances) / len(distances), len(distances)


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
            out.warning("  %s : aucune transition avec changement de code — ignoré", actor)
            dropped += 1
            continue
        value, transitions = result
        metric_map[actor] = round(value, 6)
        out.info("  %s : %.4f (%d transition(s) modifiée(s))", actor, value, transitions)

    out.info("%d étudiant(s) ignoré(s)", dropped)
    um.write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/traces_20_sept_10_11.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/CodeChangeMagnitude.csv"
    main(input_path, output_path)
