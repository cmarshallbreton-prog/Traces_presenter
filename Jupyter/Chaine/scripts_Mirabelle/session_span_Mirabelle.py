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


def calculate_session_span(actor_rows: pd.DataFrame) -> float | None:
    """
    Durée en minutes entre le premier et le dernier Run.Test de l'étudiant.

    Retourne None s'il n'y a aucun Run.Test (ou si les timestamps sont invalides).
    """
    run_test = actor_rows[actor_rows[COL_VERB] == VERB_TEST]
    if run_test.empty:
        return None

    ts = pd.to_datetime(run_test[COL_TS], errors="coerce", utc=True).dropna()
    if ts.empty:
        return None

    span_minutes = (ts.max() - ts.min()).total_seconds() / 60.0
    return float(max(span_minutes, 0.0))


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
    write_path = sys.argv[2] if len(sys.argv) > 2 else "out/SessionSpan.csv"

    df = load_csv(read_path)
    if not check_columns(df, REQUIRED_COLS):
        sys.exit(1)

    actors = df[COL_ACTOR].dropna().unique()
    out.info("%d étudiant(s) trouvé(s)", len(actors))

    metric_map: dict[str, float] = {}
    dropped = 0

    for actor in sorted(actors):
        actor_rows = df[df[COL_ACTOR] == actor]
        span = calculate_session_span(actor_rows)

        if span is None:
            out.warning("  %s : aucun Run.Test — ignoré", actor)
            dropped += 1
        else:
            metric_map[actor] = round(span, 4)
            out.info("  %s : %.1f min  (%d Run.Test)",
                     actor, span,
                     int((actor_rows[COL_VERB] == VERB_TEST).sum()))

    out.info("%d étudiant(s) ignoré(s) (aucun Run.Test)", dropped)
    write_metric("SessionSpan", metric_map, write_path)
