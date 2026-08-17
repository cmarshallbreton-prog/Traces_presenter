"""Calcule le nombre de sessions d'activité dans les traces Mirabelle.

Seuls les événements ``Run.Test`` sont utilisés. Pour un étudiant, les
événements sont triés chronologiquement et une nouvelle session commence
lorsque l'écart avec le ``Run.Test`` précédent est strictement supérieur au
seuil (5 minutes par défaut).

Sortie : ``SubjectID, SessionCount``.
"""

from __future__ import annotations

import sys

import pandas as pd

import utils_Mirabelle as um

METRIC_NAME = "SessionCount"
DEFAULT_GAP_MINUTES = um.DEFAULT_SESSION_GAP_MINUTES
REQUIRED_COLS = [um.COL_ACTOR, um.COL_VERB, um.COL_TS]


def calculate_session_count(actor_rows: pd.DataFrame, gap_minutes: float) -> int | None:
    """Compte les groupes de ``Run.Test`` séparés par plus de ``gap_minutes``."""

    run_tests = actor_rows.loc[actor_rows[um.COL_VERB] == um.VERB_TEST].copy()
    if run_tests.empty:
        return None
    sessionized = um.add_activity_session_ids(run_tests, gap_minutes=gap_minutes)
    if sessionized.empty:
        return None
    return int(sessionized[um.COL_ACTIVITY_SESSION].nunique())


def main(read_path: str, write_path: str, gap_minutes: float = DEFAULT_GAP_MINUTES) -> None:
    """Charge les traces, calcule la métrique par étudiant et écrit le CSV."""

    df = um.load_csv(read_path)
    if not um.check_columns(df, REQUIRED_COLS):
        raise SystemExit(1)

    metric_map: dict[str, int] = {}
    for actor, actor_rows in df.dropna(subset=[um.COL_ACTOR]).groupby(um.COL_ACTOR, sort=True):
        value = calculate_session_count(actor_rows, gap_minutes)
        if value is not None:
            metric_map[str(actor)] = value

    um.write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/traces_20_sept_10_11.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/SessionCount.csv"
    gap = float(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_GAP_MINUTES
    main(input_path, output_path, gap)
