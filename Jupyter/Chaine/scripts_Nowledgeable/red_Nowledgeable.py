"""Calcule la Repeated Error Density (RED) sur les traces Nowledgeable.

Les tentatives sont triées et segmentées par exercice. Les doublons portant le
même ``answerUuid`` sont retirés, les relances consécutives à code inchangé
sont ignorées, et un feedback manquant coupe la séquence.

Pour chaque séquence de ``r`` transitions consécutives partageant au moins un
type d'erreur de compilation normalisé, la contribution RED est :

    r² / (r + 1)

Comme dans ``scripts_Progsnap2/red.py``, la somme est divisée par le nombre de
transitions observables afin de comparer des étudiants ayant des volumes de
travail différents. Le résultat est compris entre 0 et 1 (1 n'est approché que
pour une très longue série de la même erreur répétée).

Usage
-----
python red_Nowledgeable.py [fichier_entree.csv] [fichier_sortie.csv]
"""

from __future__ import annotations

import csv
import html
import json
import logging
import pathlib
import re
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
COL_FEEDBACK = "recordedFeedback"
COL_CODE = "answerContent"
COL_ANSWER_UUID = "answerUuid"

REQUIRED_COLS = [COL_STUDENT, COL_EXERCISE, COL_TIMESTAMP, COL_FEEDBACK]
METRIC_NAME = "RED"

SMART_QUOTES = str.maketrans({
    "‘": "'",
    "’": "'",
    "`": "'",
    "“": '"',
    "”": '"',
})

ERROR_RE = re.compile(r"(?:fatal\s+)?error:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
LINKER_RE = re.compile(
    r"(?:undefined reference to|multiple definition of)\s+(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
QUOTED_RE = re.compile(r"'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\"")
HEX_RE = re.compile(r"\b0x[0-9a-f]+\b", re.IGNORECASE)
NUMBER_RE = re.compile(r"(?<![a-z_])[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?", re.IGNORECASE)
SPACE_RE = re.compile(r"\s+")


def parse_timestamps(series: pd.Series) -> pd.Series:
    """Convertit secondes Unix, millisecondes Unix ou dates textuelles en UTC."""
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


def parse_feedback(raw: Any) -> dict[str, Any] | None:
    """Retourne le feedback JSON sous forme de dictionnaire, sinon ``None``."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or raw.strip() == "":
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def normalize_error_type(message: str) -> str:
    """Normalise un diagnostic pour comparer son type entre tentatives."""
    text = html.unescape(str(message)).translate(SMART_QUOTES).strip().lower()
    text = re.sub(r";?\s*did you mean\s+.+?\??$", "", text, flags=re.IGNORECASE)
    text = QUOTED_RE.sub("<token>", text)
    text = HEX_RE.sub("<hex>", text)
    text = NUMBER_RE.sub("<num>", text)
    text = SPACE_RE.sub(" ", text).strip(" .;:")
    return text


def compiler_error_types(feedback: dict[str, Any]) -> frozenset[str]:
    """Extrait les diagnostics ``error:`` et les erreurs d'édition de liens."""
    stderr = feedback.get("stderr")
    if stderr is None:
        return frozenset()

    text = html.unescape(str(stderr)).translate(SMART_QUOTES)
    messages = ERROR_RE.findall(text)
    messages.extend(
        f"linker: {match}" for match in LINKER_RE.findall(text)
    )

    normalized = {
        normalize_error_type(message)
        for message in messages
        if normalize_error_type(message)
    }
    return frozenset(normalized)


def prepare_attempts(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie, déduplique, ordonne et annote les tentatives."""
    attempts = df.copy()
    attempts[COL_STUDENT] = attempts[COL_STUDENT].astype("string")
    attempts["__row_order"] = range(len(attempts))
    attempts["__timestamp"] = parse_timestamps(attempts[COL_TIMESTAMP])

    invalid_timestamps = int(attempts["__timestamp"].isna().sum())
    if invalid_timestamps:
        out.warning("%d ligne(s) avec answeredAt invalide", invalid_timestamps)

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

    attempts["__feedback"] = attempts[COL_FEEDBACK].apply(parse_feedback)
    attempts["__feedback_known"] = attempts["__feedback"].apply(
        lambda value: isinstance(value, dict)
    )
    attempts["__error_types"] = attempts["__feedback"].apply(
        lambda value: compiler_error_types(value)
        if isinstance(value, dict)
        else frozenset()
    )

    if COL_CODE in attempts.columns:
        attempts["__code"] = attempts[COL_CODE].apply(
            lambda value: None if pd.isna(value) else str(value)
        )
    else:
        attempts["__code"] = None
        out.warning(
            "Colonne %s absente : les relances à code inchangé ne seront pas filtrées",
            COL_CODE,
        )

    return attempts.sort_values(
        [COL_STUDENT, COL_EXERCISE, "__timestamp", "__row_order"],
        kind="mergesort",
    ).reset_index(drop=True)


def build_segments(student_rows: pd.DataFrame) -> list[list[int]]:
    """Construit les segments comparables d'un étudiant."""
    segments: list[list[int]] = []

    for _, exercise_rows in student_rows.groupby(COL_EXERCISE, sort=False):
        current: list[int] = []
        previous_kept_code: str | None = None

        for index, row in exercise_rows.iterrows():
            if not bool(row["__feedback_known"]):
                if current:
                    segments.append(current)
                current = []
                previous_kept_code = None
                continue

            code = row["__code"]
            if (
                current
                and code is not None
                and previous_kept_code is not None
                and code == previous_kept_code
            ):
                continue

            current.append(index)
            previous_kept_code = code

        if current:
            segments.append(current)

    return segments


def calculate_red(student_rows: pd.DataFrame) -> tuple[float, int] | None:
    """Retourne ``(RED_normalisée, nombre_de_transitions)`` ou ``None``."""
    red = 0.0
    transition_count = 0

    for segment in build_segments(student_rows):
        repeated = 0

        for first_index, second_index in zip(segment, segment[1:]):
            transition_count += 1
            first_errors = student_rows.at[first_index, "__error_types"]
            second_errors = student_rows.at[second_index, "__error_types"]

            if first_errors & second_errors:
                repeated += 1
            else:
                if repeated > 0:
                    red += (repeated ** 2) / (repeated + 1)
                repeated = 0

        if repeated > 0:
            red += (repeated ** 2) / (repeated + 1)

    if transition_count == 0:
        return None

    return red / transition_count, transition_count


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
        result = calculate_red(student_rows)

        if result is None:
            out.warning(
                "  %s : aucune transition avec feedback de compilation observable — ignoré",
                student_id,
            )
            dropped += 1
            continue

        red, transition_count = result
        metric_map[str(student_id)] = round(red, 6)
        out.info(
            "  %s : RED = %.4f (%d transition(s))",
            student_id,
            red,
            transition_count,
        )

    out.info("%d étudiant(s) ignoré(s) (aucune transition observable)", dropped)
    write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    input_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/session_13568_answers_corrige.csv"
    )
    output_path = sys.argv[2] if len(sys.argv) > 2 else "out/RED.csv"
    main(input_path, output_path)
