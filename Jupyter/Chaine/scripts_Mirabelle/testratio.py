import sys
import ast
import csv
import logging
import pathlib

import pandas as pd

logging.basicConfig(
    format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
    level=logging.INFO,
)
out = logging.getLogger()


VERB_TEST    = "Run.Test"
COL_ACTOR    = "actor"
COL_VERB     = "verb"
COL_TESTS    = "tests"

REQUIRED_COLS = [COL_ACTOR, COL_VERB, COL_TESTS]


def parse_tests(raw: str) -> list[dict]:
    """
    Parse la valeur brute de la colonne 'tests' (repr Python d'une liste de dicts).
    Retourne une liste de dicts, ou une liste vide si le parsing échoue.
    """
    if not isinstance(raw, str) or raw.strip() in ("", "[]", "nan"):
        return []
    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, list):
            return parsed
    except (ValueError, SyntaxError):
        out.debug("Parsing échoué pour : %s", raw[:80])
    return []


def calculate_test_pass_rate(actor_rows: pd.DataFrame) -> float | None:
    """
    Calcule le TestPassRate pour un étudiant donné.

    Paramètre
    ---------
    actor_rows : DataFrame filtré sur un seul acteur (toutes ses lignes du CSV)

    Retourne
    --------
    float dans [0.0, 1.0] si au moins un cas de test existe, None sinon.
    """
    run_test_rows = actor_rows[actor_rows[COL_VERB] == VERB_TEST]

    total_tests  = 0
    passed_tests = 0

    for raw in run_test_rows[COL_TESTS]:
        cases = parse_tests(raw)
        for case in cases:
            total_tests += 1
            # status est un bool : True = test passé (PassedVerdict ou PassedSetupVerdict)
            if case.get("status") is True:
                passed_tests += 1

    if total_tests == 0:
        return None

    return passed_tests / total_tests


def load_csv(path: str) -> pd.DataFrame:
    out.info("Chargement de %s …", path)
    df = pd.read_csv(path, on_bad_lines="skip", engine="python")
    out.info("  %d lignes, %d colonnes", len(df), len(df.columns))
    return df


def check_columns(df: pd.DataFrame, required: list[str]) -> bool:
    missing = [c for c in required if c not in df.columns]
    if missing:
        out.error("Colonnes manquantes dans le CSV : %s", missing)
        return False
    return True


def write_metric(name: str, metric_map: dict, path: str) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["SubjectID", name], lineterminator="\n")
        writer.writeheader()
        for subject_id, value in sorted(metric_map.items()):
            writer.writerow({"SubjectID": subject_id, name: value})
    out.info("Résultat écrit dans %s (%d étudiants)", path, len(metric_map))


def main(read_path: str, write_path: str) -> None:
    df = load_csv(read_path)

    if not check_columns(df, REQUIRED_COLS):
        sys.exit(1)

    actors = df[COL_ACTOR].dropna().unique()
    out.info("%d étudiant(s) trouvé(s)", len(actors))

    metric_map: dict[str, float] = {}
    dropped = 0

    for actor in sorted(actors):
        actor_rows = df[df[COL_ACTOR] == actor]
        rate = calculate_test_pass_rate(actor_rows)

        if rate is None:
            out.warning("  %s : aucun cas de test — ignoré", actor)
            dropped += 1
        else:
            metric_map[actor] = round(rate, 6)
            out.info("  %s : %.1f %% (%d lignes Run.Test)",
                     actor,
                     rate * 100,
                     int((actor_rows[COL_VERB] == VERB_TEST).sum()))

    out.info("%d étudiant(s) ignoré(s) (aucun Run.Test avec tests)", dropped)
    write_metric("TestPassRate", metric_map, write_path)


if __name__ == "__main__":
    _read  = sys.argv[1] if len(sys.argv) > 1 else "out.csv"
    _write = sys.argv[2] if len(sys.argv) > 2 else "out/TestPassRate.csv"
    main(_read, _write)