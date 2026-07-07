import sys

import utils_Mirabelle as um

out = um.out

TARGET_VERDICT = "ExceptionVerdict"
METRIC_NAME = "ExceptionTestRunRatio"


def run_test_contains_verdict(raw_tests, verdict: str) -> bool:
    """Vrai si la liste de cas de test contient au moins un verdict donné."""
    return any(case.get("verdict") == verdict for case in um.parse_tests(raw_tests))


def calculate_exception_run_ratio(actor_rows) -> float | None:
    """
    Calcule le ratio de Run.Test non vides contenant au moins un
    ExceptionVerdict pour un étudiant donné.

    Retourne un float dans [0.0, 1.0], ou None si aucun Run.Test non vide
    n'est disponible.
    """
    run_test_rows = actor_rows[actor_rows[um.COL_VERB] == um.VERB_TEST]

    total_non_empty_runs = 0
    runs_with_exception = 0

    for raw_tests in run_test_rows[um.COL_TESTS]:
        cases = um.parse_tests(raw_tests)
        if len(cases) == 0:
            continue

        total_non_empty_runs += 1
        if any(case.get("verdict") == TARGET_VERDICT for case in cases):
            runs_with_exception += 1

    if total_non_empty_runs == 0:
        return None

    return runs_with_exception / total_non_empty_runs


def main(read_path: str, write_path: str) -> None:
    df = um.load_csv(read_path)

    if not um.check_columns(df, [um.COL_ACTOR, um.COL_VERB, um.COL_TESTS]):
        sys.exit(1)

    actors = df[um.COL_ACTOR].dropna().unique()
    out.info("%d étudiant(s) trouvé(s)", len(actors))

    metric_map: dict[str, float] = {}
    dropped = 0

    for actor in sorted(actors):
        actor_rows = df[df[um.COL_ACTOR] == actor]
        ratio = calculate_exception_run_ratio(actor_rows)

        if ratio is None:
            out.warning("  %s : aucun Run.Test non vide — ignoré", actor)
            dropped += 1
        else:
            metric_map[actor] = round(ratio, 6)
            out.info(
                "  %s : %s = %.3f  (%d Run.Test)",
                actor,
                METRIC_NAME,
                ratio,
                int((actor_rows[um.COL_VERB] == um.VERB_TEST).sum()),
            )

    out.info("%d étudiant(s) ignoré(s) (aucun Run.Test non vide)", dropped)
    um.write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    _read = sys.argv[1] if len(sys.argv) > 1 else "data/traces_20_sept_10_11.csv"
    _write = sys.argv[2] if len(sys.argv) > 2 else "out/ExceptionTestRunRatio.csv"
    main(_read, _write)
