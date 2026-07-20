"""Calcule le nombre de fonctions traitées par étudiant dans Nowledgeable.

Une fonction est considérée comme traitée par un étudiant si au moins une des
conditions suivantes est remplie :

- une soumission contenant cette fonction possède un ``answerScore``
  strictement supérieur à 0 ;
- au moins deux versions distinctes du code de cette fonction ont été soumises.

Contrairement à ``exercise_coverage_Nowledgeable.py``, la comparaison des
versions est réalisée fonction par fonction. Une modification effectuée ailleurs
dans le fichier ne crée donc pas artificiellement une nouvelle version pour une
fonction restée inchangée.

Les définitions de fonctions C/C++ sont extraites de ``answerContent``. Les
fonctions dont le nom commence par ``test_`` sont ignorées, car elles
correspondent généralement au code de test fourni avec l'exercice. ``main``
n'est pas ignorée : certains exercices demandent précisément de modifier cette
fonction.

L'identifiant d'une fonction est le couple ``(exerciceId, nom_de_fonction)``.
Cela évite de fusionner deux fonctions homonymes appartenant à des exercices
différents. Les surcharges portant le même nom dans un même exercice sont
regroupées, comme dans la métrique Mirabelle qui se base sur le nom de fonction.

Les soumissions dupliquées portant le même ``answerUuid`` sont retirées avant
le calcul. Les fins de ligne sont harmonisées (CRLF/CR vers LF), mais les autres
changements d'espaces, de commentaires ou d'indentation sont conservés et
constituent donc une nouvelle version.

La sortie contient une ligne par étudiant, y compris pour ceux dont la
couverture est nulle.

Usage
-----
python function_coverage_Nowledgeable.py \\
    [fichier_entree.csv] [fichier_sortie.csv]
"""

from __future__ import annotations

import csv
import logging
import pathlib
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pandas as pd


logging.basicConfig(
    format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
    level=logging.INFO,
)
out = logging.getLogger()

COL_STUDENT = "studentId"
COL_EXERCISE = "exerciceId"
COL_SCORE = "answerScore"
COL_CODE = "answerContent"
COL_ANSWER_UUID = "answerUuid"

REQUIRED_COLS = [COL_STUDENT, COL_EXERCISE, COL_SCORE, COL_CODE]
METRIC_NAME = "FunctionCoverage"

# Le motif repère un identifiant suivi d'une parenthèse au début d'une ligne.
# La validation complète (parenthèses équilibrées puis accolade ouvrante avant
# tout point-virgule) est faite ensuite pour distinguer une définition d'un
# simple appel ou d'une déclaration.
FUNCTION_HEADER_RE = re.compile(
    r"(?m)^[ \t]*(?:(?:public|private|protected)\s*:\s*)?"
    r"(?P<prefix>[^\n(){};]*?)"
    r"(?P<name>~?[A-Za-z_]\w*)[ \t]*\("
)

CONTROL_KEYWORDS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "else",
    "do",
    "return",
    "sizeof",
    "alignof",
    "decltype",
    "static_assert",
}


@dataclass(frozen=True)
class FunctionDefinition:
    """Définition de fonction extraite du code source."""

    name: str
    source: str


def normalize_source(value: Any) -> str | None:
    """Harmonise uniquement les fins de ligne d'un fragment de code."""
    if pd.isna(value):
        return None
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def mask_comments_and_literals(source: str) -> str:
    """Masque commentaires et littéraux en conservant indices et retours ligne.

    Les caractères masqués deviennent des espaces. Les retours à la ligne sont
    conservés afin que les motifs ancrés en début de ligne continuent de
    fonctionner et que les indices restent alignés avec le code original.
    """
    chars = list(source)
    masked = list(source)
    i = 0
    n = len(chars)
    state = "code"
    quote = ""

    while i < n:
        char = chars[i]
        nxt = chars[i + 1] if i + 1 < n else ""

        if state == "code":
            if char == "/" and nxt == "/":
                masked[i] = masked[i + 1] = " "
                i += 2
                state = "line_comment"
                continue
            if char == "/" and nxt == "*":
                masked[i] = masked[i + 1] = " "
                i += 2
                state = "block_comment"
                continue
            if char in {'"', "'"}:
                quote = char
                masked[i] = " "
                i += 1
                state = "literal"
                continue
            i += 1
            continue

        if state == "line_comment":
            if char == "\n":
                state = "code"
            else:
                masked[i] = " "
            i += 1
            continue

        if state == "block_comment":
            if char == "*" and nxt == "/":
                masked[i] = masked[i + 1] = " "
                i += 2
                state = "code"
                continue
            if char != "\n":
                masked[i] = " "
            i += 1
            continue

        # Littéral chaîne ou caractère.
        if state == "literal":
            if char == "\\":
                masked[i] = " "
                if i + 1 < n:
                    if chars[i + 1] != "\n":
                        masked[i + 1] = " "
                    i += 2
                else:
                    i += 1
                continue
            if char == quote:
                masked[i] = " "
                i += 1
                state = "code"
                continue
            if char != "\n":
                masked[i] = " "
            i += 1

    return "".join(masked)


def find_matching(
    text: str,
    opening_index: int,
    opening_char: str,
    closing_char: str,
) -> int | None:
    """Renvoie l'indice du délimiteur fermant correspondant."""
    depth = 0
    for index in range(opening_index, len(text)):
        char = text[index]
        if char == opening_char:
            depth += 1
        elif char == closing_char:
            depth -= 1
            if depth == 0:
                return index
    return None


def find_body_opening(masked: str, closing_parenthesis: int) -> int | None:
    """Cherche l'accolade ouvrante d'une définition après sa signature.

    Un point-virgule rencontré avant l'accolade indique une déclaration ou un
    appel et non une définition. La limite évite qu'une signature incomplète ne
    capture une accolade très éloignée appartenant à un autre bloc.
    """
    search_end = min(len(masked), closing_parenthesis + 1500)
    index = closing_parenthesis + 1

    while index < search_end:
        char = masked[index]
        if char == ";":
            return None
        if char == "{":
            return index
        index += 1

    return None


def should_ignore_function(name: str, prefix: str) -> bool:
    """Indique si le candidat n'est pas une fonction utilisateur à compter."""
    plain_name = name.lstrip("~")
    if plain_name in CONTROL_KEYWORDS:
        return True
    if plain_name.startswith("test_"):
        return True
    if prefix.lstrip().startswith("#"):
        return True
    return False


def extract_function_definitions(source: str) -> list[FunctionDefinition]:
    """Extrait les définitions C/C++ trouvées dans ``source``.

    Le parseur est volontairement léger et ne remplace pas un compilateur C++,
    mais il gère les formes courantes des exercices : fonctions libres,
    méthodes définies dans une classe et constructeurs simples.
    """
    normalized = normalize_source(source)
    if normalized is None or not normalized.strip():
        return []

    masked = mask_comments_and_literals(normalized)
    definitions: list[FunctionDefinition] = []
    occupied_until = -1

    for match in FUNCTION_HEADER_RE.finditer(masked):
        if match.start() < occupied_until:
            continue

        name = match.group("name")
        prefix = match.group("prefix")
        if should_ignore_function(name, prefix):
            continue

        opening_parenthesis = match.end() - 1
        closing_parenthesis = find_matching(masked, opening_parenthesis, "(", ")")
        if closing_parenthesis is None:
            continue

        body_opening = find_body_opening(masked, closing_parenthesis)
        if body_opening is None:
            continue

        body_closing = find_matching(masked, body_opening, "{", "}")
        if body_closing is None:
            continue

        # Le fragment commence au premier caractère non blanc de la ligne de
        # signature. Cela conserve les différences d'écriture significatives,
        # tout en évitant que l'indentation externe d'une classe ne domine la
        # comparaison.
        line_start = normalized.rfind("\n", 0, match.start()) + 1
        fragment_start = line_start
        while (
            fragment_start < match.start()
            and normalized[fragment_start] in " \t"
        ):
            fragment_start += 1

        fragment = normalized[fragment_start : body_closing + 1]
        definitions.append(FunctionDefinition(name=name, source=fragment))
        occupied_until = body_closing + 1

    return definitions


def prepare_attempts(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie les soumissions et produit une ligne par fonction extraite."""
    attempts = df.copy()
    attempts[COL_STUDENT] = attempts[COL_STUDENT].astype("string")
    attempts["__score"] = pd.to_numeric(attempts[COL_SCORE], errors="coerce")

    invalid_scores = int(attempts["__score"].isna().sum())
    if invalid_scores:
        out.warning(
            "%d ligne(s) avec answerScore absent ou invalide : "
            "elles ne valideront pas le critère de score",
            invalid_scores,
        )

    attempts = attempts.dropna(subset=[COL_STUDENT, COL_EXERCISE]).copy()
    attempts = attempts[
        attempts[COL_STUDENT].astype(str).str.strip().ne("")
    ].copy()

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

    records: list[dict[str, Any]] = []
    rows_without_function = 0

    for row_index, row in attempts.iterrows():
        code = normalize_source(row.get(COL_CODE))
        if code is None:
            rows_without_function += 1
            continue

        definitions = extract_function_definitions(code)
        if not definitions:
            rows_without_function += 1
            continue

        # Une définition identique répétée dans une même soumission ne doit pas
        # créer plusieurs tentatives artificielles.
        seen_in_submission: set[tuple[str, str]] = set()
        for definition in definitions:
            signature = (definition.name, definition.source)
            if signature in seen_in_submission:
                continue
            seen_in_submission.add(signature)

            exercise_id = str(row[COL_EXERCISE])
            records.append(
                {
                    COL_STUDENT: str(row[COL_STUDENT]),
                    COL_EXERCISE: exercise_id,
                    "__row_index": row_index,
                    "__function_name": definition.name,
                    "__function_key": f"{exercise_id}::{definition.name}",
                    "__function_source": definition.source,
                    "__score": row["__score"],
                }
            )

    if rows_without_function:
        out.warning(
            "%d soumission(s) sans définition de fonction exploitable ont été ignorées",
            rows_without_function,
        )

    return pd.DataFrame.from_records(
        records,
        columns=[
            COL_STUDENT,
            COL_EXERCISE,
            "__row_index",
            "__function_name",
            "__function_key",
            "__function_source",
            "__score",
        ],
    )


def calculate_function_coverage(
    student_rows: pd.DataFrame,
) -> tuple[int, int, int]:
    """Compte les fonctions traitées par un étudiant.

    Retourne ``(total, par_score, par_versions_uniquement)``. La troisième
    valeur exclut les fonctions déjà validées par un score positif.
    """
    treated_count = 0
    treated_by_score = 0
    treated_by_versions_only = 0

    for _, function_rows in student_rows.groupby("__function_key", sort=False):
        best_score = function_rows["__score"].max(skipna=True)
        has_positive_score = pd.notna(best_score) and best_score > 0

        distinct_version_count = (
            function_rows["__function_source"].dropna().nunique()
        )
        has_two_distinct_versions = distinct_version_count >= 2

        if has_positive_score or has_two_distinct_versions:
            treated_count += 1
            if has_positive_score:
                treated_by_score += 1
            else:
                treated_by_versions_only += 1

    return treated_count, treated_by_score, treated_by_versions_only


def load_csv(path: str) -> pd.DataFrame:
    out.info("Chargement de %s …", path)
    df = pd.read_csv(
        path,
        dtype={COL_STUDENT: "string", COL_EXERCISE: "string"},
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

    # Les étudiants sont relevés avant l'extraction afin de conserver ceux pour
    # lesquels aucune fonction exploitable n'est détectée.
    students = (
        df[COL_STUDENT]
        .astype("string")
        .dropna()
        .loc[lambda values: values.str.strip().ne("")]
        .unique()
        .tolist()
    )
    function_attempts = prepare_attempts(df)

    out.info(
        "%d étudiant(s), %d tentative(s) de fonction exploitable(s)",
        len(students),
        len(function_attempts),
    )

    metric_map: dict[str, int] = {}
    for student_id in sorted(students):
        student_rows = function_attempts[
            function_attempts[COL_STUDENT] == str(student_id)
        ]
        coverage, by_score, by_versions_only = calculate_function_coverage(
            student_rows
        )

        metric_map[str(student_id)] = coverage
        out.info(
            "  %s : %d fonction(s) traitée(s) "
            "(%d avec score > 0, %d par versions distinctes uniquement)",
            student_id,
            coverage,
            by_score,
            by_versions_only,
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
        else "out/FunctionCoverage_Nowledgeable.csv"
    )
    main(input_path, output_path)
