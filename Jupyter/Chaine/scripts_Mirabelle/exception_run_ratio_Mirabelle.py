"""Part des ``Run.Test`` Mirabelle contenant au moins une exception.

Un run contribue au dénominateur s'il contient au moins un cas de test. Il
contribue au numérateur si au moins un cas porte le verdict
``ExceptionVerdict``.
"""

from __future__ import annotations

import sys

import pandas as pd

import utils_Mirabelle as um

TARGET_VERDICT = "ExceptionVerdict"
METRIC_NAME = "ExceptionTestRunRatio"
REQUIRED_COLS = [um.COL_ACTOR, um.COL_VERB, um.COL_TESTS]


def calculate_ratio(actor_rows: pd.DataFrame) -> float | None:
    """Calcule ``runs avec ExceptionVerdict / runs non vides``."""

    total = 0
    matching = 0
    for raw_tests in actor_rows.loc[actor_rows[um.COL_VERB] == um.VERB_TEST, um.COL_TESTS]:
        cases = um.parse_tests(raw_tests)
        if not cases:
            continue
        total += 1
        matching += int(any(case.get("verdict") == TARGET_VERDICT for case in cases))

    return None if total == 0 else matching / total


def main(read_path: str, write_path: str) -> None:
    df = um.load_csv(read_path)
    if not um.check_columns(df, REQUIRED_COLS):
        raise SystemExit(1)

    metric_map: dict[str, float] = {}
    for actor, actor_rows in df.dropna(subset=[um.COL_ACTOR]).groupby(um.COL_ACTOR, sort=True):
        value = calculate_ratio(actor_rows)
        if value is not None:
            metric_map[str(actor)] = round(value, 6)
    um.write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/traces_20_sept_10_11.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/ExceptionTestRunRatio.csv"
    main(input_path, output_path)
