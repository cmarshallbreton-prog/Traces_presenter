import sys
import csv
import logging
import pathlib

import pandas as pd

logging.basicConfig(
    format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
    level=logging.INFO,
)
out = logging.getLogger()

VERB_TEST = "Run.Test"
COL_ACTOR = "actor"
COL_VERB  = "verb"
COL_TS    = "timestamp.$date"

REQUIRED_COLS = [COL_ACTOR, COL_VERB, COL_TS]


def calculate_session_count(actor_rows: pd.DataFrame, gap_minutes: float = 5.0) -> int | None:
    """
    Nombre de groupes de Run.Test séparés par un silence d'au moins `gap_minutes`.

    Un seul Run.Test  →  1 session.
    Retourne None s'il n'y a aucun Run.Test (ou si les timestamps sont invalides).
    """
    run_test = actor_rows[actor_rows[COL_VERB] == VERB_TEST]
    if run_test.empty:
        return None

    ts = pd.to_datetime(run_test[COL_TS], errors="coerce", utc=True).dropna()
    if ts.empty:
        return None

    ts_sorted = ts.sort_values()
    gaps = ts_sorted.diff().dt.total_seconds().dropna()
    threshold = gap_minutes * 60.0
    return int(1 + (gaps > threshold).sum())


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
    out.info("Résultat écrit dans %s  (%d étudiant(s))", path, len(metric_map))


if __name__ == "__main__":
    read_path  = sys.argv[1] if len(sys.argv) > 1 else "data/traces_anonymisees_RGPD_2026_06_09.csv"
    write_path = sys.argv[2] if len(sys.argv) > 2 else "out/SessionCount.csv"
    gap_minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0

    df = load_csv(read_path)
    if not check_columns(df, REQUIRED_COLS):
        sys.exit(1)

    actors = df[COL_ACTOR].dropna().unique()
    out.info("%d étudiant(s) trouvé(s)", len(actors))

    metric_map: dict[str, int] = {}
    dropped = 0

    for actor in sorted(actors):
        actor_rows = df[df[COL_ACTOR] == actor]
        count = calculate_session_count(actor_rows, gap_minutes=gap_minutes)

        if count is None:
            out.warning("  %s : aucun Run.Test — ignoré", actor)
            dropped += 1
        else:
            metric_map[actor] = count
            out.info("  %s : %d session(s)  (%d Run.Test)",
                     actor, count,
                     int((actor_rows[COL_VERB] == VERB_TEST).sum()))

    out.info("%d étudiant(s) ignoré(s) (aucun Run.Test)", dropped)
    write_metric("SessionCount", metric_map, write_path)
