"""Calcule le taux de transitions productives dans Mirabelle.

Ici la transition est définie au niveau ``Run.Test`` / fichier (et non au
niveau d'une fonction), car ``P_codeState`` contient l'état du fichier entier.
Deux Run.Test consécutifs du même fichier et de la même session d’activité (pause > 5 min) sont
comparables seulement si :

1. leur ``P_codeState`` est disponible et a changé ;
2. leur suite de tests est strictement la même, définie par les triplets
   ``(nom de fonction, tested_line, expected_result)`` avec leur multiplicité ;
3. les deux Run.Test contiennent des statuts de tests exploitables.

Pour un Run.Test :

    pass_rate = nombre de cas avec status réussi / nombre de cas exploitables

Une transition est productive si ``pass_rate_(i+1) > pass_rate_i``.

    ProductiveTransitionRate = transitions productives / transitions comparables

Le contrôle de l'identité de la suite de tests est essentiel dans Mirabelle :
les tests sont écrits par les étudiants. Sans ce filtre, une variation du taux
de réussite pourrait venir d'un ajout ou d'une modification de test plutôt que
d'une amélioration du programme.

Usage
-----
python productive_transition_rate_Mirabelle.py [entree.csv] [sortie.csv]
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
METRIC_NAME = "ProductiveTransitionRate"
REQUIRED_COLS = [
    um.COL_ACTOR,
    um.COL_VERB,
    um.COL_TESTS,
    um.COL_TS,
    um.COL_CODESTATE,
]


def status_is_passed(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool) and not pd.isna(value):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "passed", "pass"}
    return False


def normalize_code(value: Any) -> str | None:
    if pd.isna(value):
        return None
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def extract_function_name(case: dict[str, Any]) -> str:
    for key in ("name", "tested_line"):
        raw = case.get(key)
        if isinstance(raw, str) and raw.strip():
            match = FUNCTION_RE.match(raw)
            if match:
                return match.group(1)
    return "<fonction_inconnue>"


def infer_filename(row: pd.Series, cases: list[dict[str, Any]]) -> str | None:
    fallback = row.get(um.COL_FILE)
    if pd.notna(fallback) and str(fallback).strip():
        return os.path.basename(str(fallback).strip())
    for case in cases:
        raw = case.get("filename")
        if isinstance(raw, str) and raw.strip():
            return os.path.basename(raw.strip())
    return None


def test_identity(case: dict[str, Any]) -> tuple[str, str, str]:
    """Identité d'un test sans ``lineno``, qui bouge avec les insertions."""
    return (
        extract_function_name(case),
        str(case.get("tested_line", "")).strip(),
        str(case.get("expected_result", "")).strip(),
    )


def prepare_attempts(df: pd.DataFrame) -> pd.DataFrame:
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
        cases = [
            case for case in um.parse_tests(row[um.COL_TESTS])
            if isinstance(case, dict) and "status" in case
        ]
        if not cases:
            continue
        code = normalize_code(row.get(um.COL_CODESTATE))
        if code is None:
            continue
        filename = infer_filename(row, cases)
        if filename is None:
            continue

        passed = sum(status_is_passed(case.get("status")) for case in cases)
        signature = tuple(sorted(test_identity(case) for case in cases))
        records.append({
            um.COL_ACTOR: str(row[um.COL_ACTOR]),
            "__session": str(row[um.COL_ACTIVITY_SESSION]),
            "__filename": filename,
            "__timestamp": row["__timestamp"],
            "__row_order": row["__row_order"],
            "__code": code,
            "__test_signature": signature,
            "__pass_rate": passed / len(cases),
        })

    columns = [
        um.COL_ACTOR, "__session", "__filename", "__timestamp", "__row_order",
        "__code", "__test_signature", "__pass_rate",
    ]
    attempts = pd.DataFrame.from_records(records, columns=columns)
    return attempts.sort_values(
        [um.COL_ACTOR, "__session", "__filename", "__timestamp", "__row_order"],
        kind="mergesort",
    ).reset_index(drop=True)


def calculate_metric(actor_rows: pd.DataFrame) -> tuple[float, int, int] | None:
    productive = 0
    comparable = 0

    for _, unit_rows in actor_rows.groupby(["__session", "__filename"], sort=False):
        previous = None
        for _, current in unit_rows.iterrows():
            if previous is not None:
                if (
                    previous["__code"] != current["__code"]
                    and previous["__test_signature"] == current["__test_signature"]
                ):
                    comparable += 1
                    if float(current["__pass_rate"]) > float(previous["__pass_rate"]):
                        productive += 1
            previous = current

    if comparable == 0:
        return None
    return productive / comparable, productive, comparable


def main(read_path: str, write_path: str) -> None:
    df = um.load_csv(read_path)
    if not um.check_columns(df, REQUIRED_COLS):
        sys.exit(1)

    attempts = prepare_attempts(df)
    actors = df[um.COL_ACTOR].dropna().astype(str).unique().tolist()
    metric_map: dict[str, float] = {}
    dropped = 0

    for actor in sorted(actors):
        actor_rows = attempts[attempts[um.COL_ACTOR] == actor]
        result = calculate_metric(actor_rows)
        if result is None:
            out.warning("  %s : aucune transition comparable — ignoré", actor)
            dropped += 1
            continue
        rate, productive, total = result
        metric_map[actor] = round(rate, 6)
        out.info("  %s : %.1f %% (%d/%d transitions)", actor, rate * 100, productive, total)

    out.info("%d étudiant(s) ignoré(s)", dropped)
    um.write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/traces_20_sept_10_11.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/ProductiveTransitionRate.csv"
    main(input_path, output_path)
