"""Calcule la progression moyenne du score de chaque étudiant.

La granularité retenue est l'exercice. Pour chaque couple étudiant-exercice
ayant au moins deux tentatives distinctes, la progression est définie par :

    progression_exercice = dernier_answerScore - premier_answerScore

Le ScoreProgression de l'étudiant est la moyenne de ces progressions par
exercice. Il est donc borné entre -1 et 1 :

- ``-1`` : passage de 100 % à 0 % sur tous les exercices observables ;
- ``0``  : aucune variation moyenne entre première et dernière tentative ;
- ``1``  : passage de 0 % à 100 % sur tous les exercices observables.

Les valeurs intermédiaires de ``answerScore`` sont conservées telles quelles,
ce qui permet de prendre en compte les validations partielles. Les exercices
avec une seule tentative ne permettent pas de mesurer une progression et sont
ignorés. Les soumissions dupliquées portant le même ``answerUuid`` sont
comptées une seule fois.

Usage
-----
python score_progression_Nowledgeable.py [fichier_entree.csv] [fichier_sortie.csv]
"""

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
COL_EXERCISE = "exerciceId"
COL_TIMESTAMP = "answeredAt"
COL_SCORE = "answerScore"
COL_ANSWER_UUID = "answerUuid"

REQUIRED_COLS = [COL_STUDENT, COL_EXERCISE, COL_TIMESTAMP, COL_SCORE]
METRIC_NAME = "ScoreProgression"


def parse_timestamps(series: pd.Series) -> pd.Series:
    """Convertit une série de dates Nowledgeable en timestamps UTC.

    ``answeredAt`` est actuellement exprimé en secondes Unix, mais cette
    fonction accepte également des millisecondes Unix et des dates textuelles.
    Les valeurs non convertibles deviennent ``NaT``.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns, UTC]")

    numeric_mask = numeric.notna()
    if numeric_mask.any():
        # Les timestamps Unix en millisecondes sont actuellement de l'ordre de
        # 10^12, alors que les secondes sont de l'ordre de 10^9.
        milliseconds_mask = numeric_mask & (numeric.abs() >= 100_000_000_000)
        seconds_mask = numeric_mask & ~milliseconds_mask

        if seconds_mask.any():
            parsed.loc[seconds_mask] = pd.to_datetime(
                numeric.loc[seconds_mask], unit="s", errors="coerce", utc=True
            )
        if milliseconds_mask.any():
            parsed.loc[milliseconds_mask] = pd.to_datetime(
                numeric.loc[milliseconds_mask], unit="ms", errors="coerce", utc=True
            )

    text_mask = ~numeric_mask & series.notna()
    if text_mask.any():
        parsed.loc[text_mask] = pd.to_datetime(
            series.loc[text_mask], errors="coerce", utc=True
        )

    return parsed


def prepare_attempts(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie, déduplique et ordonne les tentatives exploitables."""
    attempts = df.copy()
    attempts["__row_order"] = range(len(attempts))
    attempts["__score"] = pd.to_numeric(attempts[COL_SCORE], errors="coerce")
    attempts["__timestamp"] = parse_timestamps(attempts[COL_TIMESTAMP])

    invalid_scores = attempts["__score"].isna().sum()
    invalid_timestamps = attempts["__timestamp"].isna().sum()
    if invalid_scores:
        out.warning("%d ligne(s) avec answerScore invalide", invalid_scores)
    if invalid_timestamps:
        out.warning("%d ligne(s) avec answeredAt invalide", invalid_timestamps)

    attempts = attempts.dropna(
        subset=[COL_STUDENT, COL_EXERCISE, "__score", "__timestamp"]
    ).copy()

    outside_range = ~attempts["__score"].between(0.0, 1.0)
    if outside_range.any():
        out.warning(
            "%d score(s) hors de [0, 1] ont été ramenés dans cet intervalle",
            int(outside_range.sum()),
        )
        attempts["__score"] = attempts["__score"].clip(0.0, 1.0)

    if COL_ANSWER_UUID in attempts.columns:
        has_uuid = attempts[COL_ANSWER_UUID].notna() & (
            attempts[COL_ANSWER_UUID].astype(str).str.strip() != ""
        )
        duplicated_uuid = has_uuid & attempts.duplicated(
            subset=[COL_ANSWER_UUID], keep="first"
        )
        duplicate_count = int(duplicated_uuid.sum())
        if duplicate_count:
            out.info(
                "%d soumission(s) dupliquée(s) par answerUuid ont été retirées",
                duplicate_count,
            )
            attempts = attempts.loc[~duplicated_uuid].copy()

    # En cas de timestamps identiques, l’ordre des lignes du CSV sert de
    # départage, car un UUID aléatoire ne porte aucune information temporelle.
    sort_columns = [
        COL_STUDENT,
        COL_EXERCISE,
        "__timestamp",
        "__row_order",
    ]
    return attempts.sort_values(sort_columns, kind="mergesort")


def calculate_score_progression(
    student_rows: pd.DataFrame,
) -> tuple[float, int, int] | None:
    """Calcule le ScoreProgression d'un étudiant.

    Retourne ``(score, exercices_utilises, tentatives_utilisees)``. Un exercice
    est utilisé seulement s'il contient au moins deux tentatives distinctes.
    Retourne ``None`` lorsqu'aucun exercice ne permet de mesurer une évolution.
    """
    exercise_progressions: list[float] = []
    used_attempts = 0

    for _, exercise_rows in student_rows.groupby(COL_EXERCISE, sort=False):
        if len(exercise_rows) < 2:
            continue

        first_score = float(exercise_rows.iloc[0]["__score"])
        last_score = float(exercise_rows.iloc[-1]["__score"])
        exercise_progressions.append(last_score - first_score)
        used_attempts += len(exercise_rows)

    if not exercise_progressions:
        return None

    score = sum(exercise_progressions) / len(exercise_progressions)
    # Protection contre d'éventuels très petits dépassements flottants.
    score = min(max(score, -1.0), 1.0)
    return score, len(exercise_progressions), used_attempts


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


def write_metric(name: str, metric_map: dict[str, float], path: str) -> None:
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


def main(read_path: str, write_path: str) -> None:
    df = load_csv(read_path)

    if not check_columns(df, REQUIRED_COLS):
        sys.exit(1)

    attempts = prepare_attempts(df)
    students = attempts[COL_STUDENT].dropna().unique().tolist()
    out.info("%d étudiant(s) trouvé(s)", len(students))

    metric_map: dict[str, float] = {}
    dropped = 0

    for student_id in sorted(students):
        student_rows = attempts[attempts[COL_STUDENT] == student_id]
        result = calculate_score_progression(student_rows)

        if result is None:
            out.warning(
                "  %s : aucun exercice avec au moins deux tentatives — ignoré",
                student_id,
            )
            dropped += 1
            continue

        score, exercise_count, attempt_count = result
        metric_map[str(student_id)] = round(score, 6)
        out.info(
            "  %s : %+.4f (%d exercice(s), %d tentative(s))",
            student_id,
            score,
            exercise_count,
            attempt_count,
        )

    out.info(
        "%d étudiant(s) ignoré(s) (progression non mesurable)",
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
        sys.argv[2] if len(sys.argv) > 2 else "out/ScoreProgression.csv"
    )
    main(input_path, output_path)
