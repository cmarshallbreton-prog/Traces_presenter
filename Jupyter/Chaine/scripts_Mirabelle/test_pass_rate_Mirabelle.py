"""Calcule le taux global de réussite des cas de test Mirabelle.

Les tests de Mirabelle sont écrits librement par les étudiants. Chaque cas de
la colonne ``tests`` d'un événement ``Run.Test`` est compté comme une exécution
de test. Un cas est considéré réussi lorsque ``status`` vaut vrai/1 ou que le
``verdict`` commence par ``Passed``.

La métrique est :

    TestPassRate = nombre de cas réussis / nombre de cas observables

Un même test réexécuté plusieurs fois est compté plusieurs fois. Un étudiant
sans cas de test exploitable est omis de la sortie.
"""

from __future__ import annotations

import sys
from typing import Any

import pandas as pd

import utils_Mirabelle as um

METRIC_NAME = "TestPassRate"
REQUIRED_COLS = [um.COL_ACTOR, um.COL_VERB, um.COL_TESTS]


def is_passed(case: dict[str, Any]) -> bool:
    """Interprète de façon robuste les deux codages de réussite disponibles."""

    status = case.get("status")
    if status is True:
        return True
    if isinstance(status, (int, float)) and not isinstance(status, bool) and pd.notna(status):
        return status == 1
    if isinstance(status, str) and status.strip().lower() in {"true", "1", "pass", "passed"}:
        return True

    verdict = case.get("verdict")
    return isinstance(verdict, str) and verdict.lower().startswith("passed")


def calculate_test_pass_rate(actor_rows: pd.DataFrame) -> float | None:
    """Calcule la proportion de cas réussis sur tous les ``Run.Test`` non vides."""

    passed = 0
    total = 0
    run_tests = actor_rows[actor_rows[um.COL_VERB] == um.VERB_TEST]

    for raw_tests in run_tests[um.COL_TESTS]:
        for case in um.parse_tests(raw_tests):
            if not isinstance(case, dict):
                continue
            # Un cas sans statut ni verdict ne permet pas de déterminer un
            # résultat et n'entre donc pas au dénominateur.
            if "status" not in case and "verdict" not in case:
                continue
            total += 1
            passed += int(is_passed(case))

    if total == 0:
        return None
    return passed / total


def main(read_path: str, write_path: str) -> None:
    df = um.load_csv(read_path)
    if not um.check_columns(df, REQUIRED_COLS):
        raise SystemExit(1)

    metric_map: dict[str, float] = {}
    for actor, actor_rows in df.dropna(subset=[um.COL_ACTOR]).groupby(um.COL_ACTOR, sort=True):
        value = calculate_test_pass_rate(actor_rows)
        if value is not None:
            metric_map[str(actor)] = round(value, 6)

    um.write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/traces_20_sept_10_11.csv"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/TestPassRate.csv"
    main(input_path, output_path)
