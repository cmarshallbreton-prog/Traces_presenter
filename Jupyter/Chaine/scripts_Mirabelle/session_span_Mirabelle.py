"""Calcule l'étendue temporelle des activités de test Mirabelle.

La métrique est la durée moyenne, en minutes, des sessions d'activité de
``Run.Test`` définies par le même seuil de 5 minutes que ``SessionCount``.
Les pauses qui déclenchent une nouvelle session ne sont donc pas incluses dans
la durée de la session précédente.

Sortie : ``SubjectID, SessionSpanMinutes``.
"""

from __future__ import annotations

import sys

import pandas as pd

import utils_Mirabelle as um

METRIC_NAME = "SessionSpanMinutes"
REQUIRED_COLS = [um.COL_ACTOR, um.COL_VERB, um.COL_TS]


def calculate_session_span(
    actor_rows: pd.DataFrame,
    gap_minutes: float = um.DEFAULT_SESSION_GAP_MINUTES,
) -> float | None:
    """Retourne la durée moyenne des sessions d'activité en minutes."""

    run_tests = actor_rows.loc[actor_rows[um.COL_VERB] == um.VERB_TEST].copy()
    if run_tests.empty:
        return None
    sessionized = um.add_activity_session_ids(run_tests, gap_minutes=gap_minutes)
    if sessionized.empty:
        return None
    sessionized["__timestamp"] = pd.to_datetime(sessionized[um.COL_TS], errors="coerce", utc=True)
    spans = sessionized.groupby(um.COL_ACTIVITY_SESSION)["__timestamp"].agg(
        lambda x: max((x.max() - x.min()).total_seconds() / 60.0, 0.0)
    )
    if spans.empty:
        return None
    return float(spans.mean())


def main(read_path: str, write_path: str) -> None:
    df = um.load_csv(read_path)
    if not um.check_columns(df, REQUIRED_COLS):
        raise SystemExit(1)

    metric_map: dict[str, float] = {}
    for actor, actor_rows in df.dropna(subset=[um.COL_ACTOR]).groupby(um.COL_ACTOR, sort=True):
        value = calculate_session_span(actor_rows)
        if value is not None:
            metric_map[str(actor)] = round(value, 6)

    um.write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/traces_20_sept_10_11.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/SessionSpanMinutes.csv"
    main(input_path, output_path)
