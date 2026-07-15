"""Calcule le nombre de sessions d'activité de chaque étudiant Nowledgeable.

Une session est un groupe de soumissions consécutives séparées entre elles par
au plus ``gap_minutes`` minutes. Une nouvelle session commence lorsque le temps
écoulé depuis la soumission précédente est strictement supérieur au seuil.

Le calcul est réalisé par étudiant, tous exercices confondus. Chaque ligne
valide du fichier Nowledgeable représente une activité. Les doublons de collecte
portant le même ``answerUuid`` sont retirés avant le calcul.

Exemple avec un seuil de 5 minutes :

    10:00, 10:03, 10:08, 10:14  ->  2 sessions

Les trois premières activités appartiennent à la même session : les écarts
successifs sont de 3 puis 5 minutes. L'écart de 6 minutes avant 10:14 démarre
une nouvelle session.

Usage
-----
python session_count_Nowledgeable.py \
    [fichier_entree.csv] [fichier_sortie.csv] [seuil_minutes]
"""

from __future__ import annotations

import csv
import logging
import pathlib
import sys

import pandas as pd


logging.basicConfig(
    format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
    level=logging.INFO,
)
out = logging.getLogger()

COL_STUDENT = "studentId"
COL_TIMESTAMP = "answeredAt"
COL_ANSWER_UUID = "answerUuid"

REQUIRED_COLS = [COL_STUDENT, COL_TIMESTAMP]
METRIC_NAME = "SessionCount"
DEFAULT_GAP_MINUTES = 5.0


def parse_timestamps(series: pd.Series) -> pd.Series:
    """Convertit ``answeredAt`` en timestamps UTC.

    La fonction accepte les secondes Unix, les millisecondes Unix et les dates
    textuelles. Les valeurs non convertibles deviennent ``NaT``.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns, UTC]")

    numeric_mask = numeric.notna()
    if numeric_mask.any():
        milliseconds_mask = numeric_mask & (numeric.abs() >= 100_000_000_000)
        seconds_mask = numeric_mask & ~milliseconds_mask

        if seconds_mask.any():
            parsed.loc[seconds_mask] = pd.to_datetime(
                numeric.loc[seconds_mask],
                unit="s",
                errors="coerce",
                utc=True,
            )

        if milliseconds_mask.any():
            parsed.loc[milliseconds_mask] = pd.to_datetime(
                numeric.loc[milliseconds_mask],
                unit="ms",
                errors="coerce",
                utc=True,
            )

    text_mask = ~numeric_mask & series.notna()
    if text_mask.any():
        parsed.loc[text_mask] = pd.to_datetime(
            series.loc[text_mask],
            errors="coerce",
            utc=True,
        )

    return parsed


def prepare_activities(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie, déduplique et ordonne les activités exploitables."""
    activities = df.copy()
    activities[COL_STUDENT] = activities[COL_STUDENT].astype("string")
    activities["__row_order"] = range(len(activities))
    activities["__timestamp"] = parse_timestamps(activities[COL_TIMESTAMP])

    invalid_timestamps = int(activities["__timestamp"].isna().sum())
    if invalid_timestamps:
        out.warning(
            "%d ligne(s) avec answeredAt invalide ont été ignorées",
            invalid_timestamps,
        )

    activities = activities.dropna(
        subset=[COL_STUDENT, "__timestamp"]
    ).copy()

    if COL_ANSWER_UUID in activities.columns:
        has_uuid = activities[COL_ANSWER_UUID].notna() & (
            activities[COL_ANSWER_UUID].astype(str).str.strip() != ""
        )
        duplicated_uuid = has_uuid & activities.duplicated(
            subset=[COL_ANSWER_UUID],
            keep="first",
        )
        duplicate_count = int(duplicated_uuid.sum())

        if duplicate_count:
            out.info(
                "%d activité(s) dupliquée(s) par answerUuid ont été retirées",
                duplicate_count,
            )
            activities = activities.loc[~duplicated_uuid].copy()

    # L'ordre initial du CSV départage les timestamps identiques.
    return activities.sort_values(
        [COL_STUDENT, "__timestamp", "__row_order"],
        kind="mergesort",
    ).reset_index(drop=True)


def calculate_session_count(
    student_rows: pd.DataFrame,
    gap_minutes: float = DEFAULT_GAP_MINUTES,
) -> int | None:
    """Compte les groupes d'activités séparés par plus de ``gap_minutes``.

    Une activité isolée constitue une session. ``None`` est retourné lorsqu'il
    n'existe aucune activité horodatée exploitable pour l'étudiant.
    """
    if gap_minutes < 0:
        raise ValueError("gap_minutes doit être positif ou nul")

    timestamps = student_rows["__timestamp"].dropna().sort_values()
    if timestamps.empty:
        return None

    gaps_seconds = timestamps.diff().dt.total_seconds().dropna()
    threshold_seconds = gap_minutes * 60.0

    return int(1 + (gaps_seconds > threshold_seconds).sum())


def load_csv(path: str) -> pd.DataFrame:
    out.info("Chargement de %s …", path)
    df = pd.read_csv(
        path,
        dtype={COL_STUDENT: "string"},
        on_bad_lines="skip",
        engine="python",
    )
    out.info("  %d lignes, %d colonnes", len(df), len(df.columns))
    return df


def check_columns(df: pd.DataFrame, required: list[str]) -> bool:
    missing = [column for column in required if column not in df.columns]
    if missing:
        out.error("Colonnes manquantes dans le CSV : %s", missing)
        return False
    return True


def write_metric(name: str, metric_map: dict[str, int], path: str) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["SubjectID", name],
            lineterminator="\n",
        )
        writer.writeheader()

        for subject_id, value in sorted(metric_map.items(), key=lambda item: item[0]):
            writer.writerow({"SubjectID": subject_id, name: value})

    out.info("Résultat écrit dans %s (%d étudiants)", path, len(metric_map))


def main(read_path: str, write_path: str, gap_minutes: float) -> None:
    df = load_csv(read_path)

    if not check_columns(df, REQUIRED_COLS):
        sys.exit(1)

    if gap_minutes < 0:
        out.error("Le seuil en minutes doit être positif ou nul")
        sys.exit(1)

    activities = prepare_activities(df)
    students = activities[COL_STUDENT].dropna().unique().tolist()
    out.info("%d étudiant(s) trouvé(s)", len(students))

    metric_map: dict[str, int] = {}
    dropped = 0

    for student_id in sorted(students):
        student_rows = activities[activities[COL_STUDENT] == student_id]
        count = calculate_session_count(
            student_rows,
            gap_minutes=gap_minutes,
        )

        if count is None:
            out.warning("  %s : aucune activité horodatée — ignoré", student_id)
            dropped += 1
            continue

        metric_map[str(student_id)] = count
        out.info(
            "  %s : %d session(s) (%d activité(s))",
            student_id,
            count,
            len(student_rows),
        )

    out.info(
        "%d étudiant(s) ignoré(s) (aucune activité horodatée)",
        dropped,
    )
    write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    input_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/session_13568_answers_corrige.csv"
    )
    output_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "out/SessionCount.csv"
    )
    gap = float(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_GAP_MINUTES

    main(input_path, output_path, gap)
