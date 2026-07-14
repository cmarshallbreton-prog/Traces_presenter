"""Calcule la plus longue série de tentatives sans changement de code.

Pour chaque étudiant, les tentatives sont séparées par exercice et triées selon
``answeredAt``. Le script recherche ensuite la plus longue suite de soumissions
consécutives dont ``answerContent`` est strictement identique.

La métrique compte toutes les tentatives de la série, y compris la première :

- codes ``A, A, A`` : valeur 3 ;
- codes ``A, A, B, B`` : valeur 2 ;
- aucun code soumis deux fois de suite : valeur 1.

Les comparaisons sont effectuées à l'intérieur d'un même exercice uniquement.
Les doublons de collecte portant le même ``answerUuid`` sont retirés avant le
calcul. Seuls les caractères de fin de ligne sont harmonisés (CRLF/CR vers LF) :
toute autre modification, y compris un changement d'espaces, est considérée
comme un changement de code. Une valeur ``answerContent`` manquante interrompt
la série et n'est pas comptée.

Usage
-----
python max_unchanged_code_attempts_Nowledgeable.py \
    [fichier_entree.csv] [fichier_sortie.csv]
"""

from __future__ import annotations

import csv
import logging
import pathlib
import sys
from typing import Any

import pandas as pd


logging.basicConfig(
    format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
    level=logging.INFO,
)
out = logging.getLogger()

COL_STUDENT = "studentId"
COL_EXERCISE = "exerciceId"
COL_TIMESTAMP = "answeredAt"
COL_ANSWER_UUID = "answerUuid"
COL_CODE = "answerContent"

REQUIRED_COLS = [COL_STUDENT, COL_EXERCISE, COL_TIMESTAMP, COL_CODE]
METRIC_NAME = "MaxUnchangedCodeAttempts"


def parse_timestamps(series: pd.Series) -> pd.Series:
    """Convertit les dates Nowledgeable en timestamps UTC.

    ``answeredAt`` peut être exprimé en secondes Unix, en millisecondes Unix,
    ou sous forme textuelle. Les valeurs non convertibles deviennent ``NaT``.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns, UTC]")

    numeric_mask = numeric.notna()
    if numeric_mask.any():
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


def normalize_code(value: Any) -> str | None:
    """Retourne le code comparable ou ``None`` lorsque le code est absent.

    Les fins de ligne sont harmonisées pour éviter qu'un simple changement de
    format de fichier soit interprété comme une modification du code. Aucun
    autre nettoyage n'est effectué : espaces, commentaires et indentation font
    partie du contenu comparé.
    """
    if pd.isna(value):
        return None
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def prepare_attempts(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie, déduplique, ordonne et annote les tentatives."""
    attempts = df.copy()
    attempts[COL_STUDENT] = attempts[COL_STUDENT].astype("string")
    attempts["__row_order"] = range(len(attempts))
    attempts["__timestamp"] = parse_timestamps(attempts[COL_TIMESTAMP])
    attempts["__code"] = attempts[COL_CODE].apply(normalize_code)

    invalid_timestamps = int(attempts["__timestamp"].isna().sum())
    if invalid_timestamps:
        out.warning("%d ligne(s) avec answeredAt invalide", invalid_timestamps)

    missing_codes = int(attempts["__code"].isna().sum())
    if missing_codes:
        out.warning(
            "%d ligne(s) sans answerContent : elles interrompront les séries",
            missing_codes,
        )

    attempts = attempts.dropna(
        subset=[COL_STUDENT, COL_EXERCISE, "__timestamp"]
    ).copy()

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

    # L'ordre initial du CSV départage les timestamps identiques.
    return attempts.sort_values(
        [COL_STUDENT, COL_EXERCISE, "__timestamp", "__row_order"],
        kind="mergesort",
    ).reset_index(drop=True)


def calculate_max_unchanged_attempts(student_rows: pd.DataFrame) -> int | None:
    """Calcule la plus longue série identique d'un étudiant.

    Retourne ``None`` si l'étudiant ne possède aucun ``answerContent``
    exploitable. Une tentative isolée compte comme une série de longueur 1.
    """
    maximum = 0

    for _, exercise_rows in student_rows.groupby(COL_EXERCISE, sort=False):
        previous_code: str | None = None
        current_streak = 0

        for code in exercise_rows["__code"]:
            if code is None:
                previous_code = None
                current_streak = 0
                continue

            if current_streak > 0 and code == previous_code:
                current_streak += 1
            else:
                current_streak = 1

            previous_code = code
            maximum = max(maximum, current_streak)

    return maximum if maximum > 0 else None


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


def main(read_path: str, write_path: str) -> None:
    df = load_csv(read_path)

    if not check_columns(df, REQUIRED_COLS):
        sys.exit(1)

    attempts = prepare_attempts(df)
    students = attempts[COL_STUDENT].dropna().unique().tolist()
    out.info("%d étudiant(s) trouvé(s)", len(students))

    metric_map: dict[str, int] = {}
    dropped = 0

    for student_id in sorted(students):
        student_rows = attempts[attempts[COL_STUDENT] == student_id]
        maximum = calculate_max_unchanged_attempts(student_rows)

        if maximum is None:
            out.warning("  %s : aucun code exploitable — ignoré", student_id)
            dropped += 1
            continue

        metric_map[str(student_id)] = maximum
        out.info("  %s : %d tentative(s) consécutive(s)", student_id, maximum)

    out.info("%d étudiant(s) ignoré(s) (aucun code exploitable)", dropped)
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
        else "out/MaxUnchangedCodeAttempts.csv"
    )
    main(input_path, output_path)
