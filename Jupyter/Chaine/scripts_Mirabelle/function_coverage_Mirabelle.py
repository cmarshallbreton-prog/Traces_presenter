"""Calcule le nombre de fonctions traitées par étudiant dans Mirabelle.

Une fonction est considérée comme traitée si au moins une des conditions
suivantes est remplie :

- au moins un de ses cas de test a réussi (``status`` vrai ou égal à 1) ;
- elle apparaît dans des ``Run.Test`` associés à au moins deux valeurs
  distinctes de ``P_codeState``.

Les fonctions testées sont extraites du champ ``name`` de chaque cas contenu
dans la colonne ``tests``. Par exemple, ``"cout_location(nb_jours, nb_km)"``
est normalisé en ``"cout_location"``.

Pour éviter de fusionner des fonctions homonymes présentes dans des fichiers
différents (par exemple plusieurs fonctions ``main``), l'identifiant utilisé
est le couple ``(fichier, nom_de_fonction)``. Le fichier vient en priorité du
champ ``filename`` du cas de test, puis de la colonne ``filename_infere``.

La sortie contient une ligne par étudiant, y compris pour ceux dont la
couverture est nulle.

Usage
-----
python function_coverage_Mirabelle.py \\
    [fichier_entree.csv] [fichier_sortie.csv] \\
    [colonne_code_state]
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any

import pandas as pd

import utils_Mirabelle as um


out = um.out

COL_EVENT_ID = "_id.$oid"
COL_CODE_STATE = um.COL_CODESTATE
METRIC_NAME = "FunctionCoverage"

# Reconnaît un nom Python placé au début d'une signature ou d'un appel.
FUNCTION_NAME_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:\(|$)")


def status_is_passed(value: Any) -> bool:
    """Retourne True pour les représentations usuelles d'un test réussi."""
    if value is True:
        return True
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not pd.isna(value):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "passed", "pass"}
    return False


def extract_function_name(case: dict[str, Any]) -> str | None:
    """Extrait le nom canonique d'une fonction depuis un cas de test.

    Le champ ``name`` est prioritaire. ``tested_line`` sert de repli pour les
    rares cas où ``name`` serait absent ou mal formé.
    """
    for key in ("name", "tested_line"):
        raw = case.get(key)
        if not isinstance(raw, str) or not raw.strip():
            continue
        match = FUNCTION_NAME_RE.match(raw)
        if match:
            return match.group(1)
    return None


def extract_test_filename(case: dict[str, Any], fallback: Any) -> str:
    """Renvoie un nom de fichier court pour distinguer les homonymes."""
    raw_filename = case.get("filename")
    if isinstance(raw_filename, str) and raw_filename.strip():
        return os.path.basename(raw_filename.strip())

    if pd.notna(fallback):
        fallback_text = str(fallback).strip()
        if fallback_text:
            return os.path.basename(fallback_text)

    # Les données sans fichier restent exploitables. Elles seront regroupées
    # uniquement par nom de fonction.
    return "<fichier_inconnu>"


def prepare_function_attempts(
    df: pd.DataFrame,
    code_state_col: str = COL_CODE_STATE,
) -> pd.DataFrame:
    """Produit une ligne par événement ``Run.Test`` et fonction testée.

    Plusieurs cas de test d'une même fonction dans le même événement sont
    agrégés : la fonction est marquée réussie si au moins un de ces cas passe.
    """
    attempts = df[df[um.COL_VERB] == um.VERB_TEST].copy()

    attempts[um.COL_ACTOR] = attempts[um.COL_ACTOR].astype("string")
    attempts = attempts.dropna(subset=[um.COL_ACTOR]).copy()
    attempts = attempts[attempts[um.COL_ACTOR].str.strip().ne("")].copy()

    if COL_EVENT_ID in attempts.columns:
        has_event_id = attempts[COL_EVENT_ID].notna() & (
            attempts[COL_EVENT_ID].astype(str).str.strip() != ""
        )
        duplicated_event = has_event_id & attempts.duplicated(
            subset=[COL_EVENT_ID], keep="first"
        )
        duplicate_count = int(duplicated_event.sum())
        if duplicate_count:
            out.info(
                "%d événement(s) Run.Test dupliqué(s) par %s ont été retirés",
                duplicate_count,
                COL_EVENT_ID,
            )
            attempts = attempts.loc[~duplicated_event].copy()

    records: list[dict[str, Any]] = []
    unparsed_test_events = 0
    missing_function_cases = 0

    for row_index, row in attempts.iterrows():
        cases = um.parse_tests(row[um.COL_TESTS])
        if not cases:
            unparsed_test_events += 1
            continue

        # Agrégation locale : une seule ligne par fonction pour ce Run.Test.
        event_functions: dict[tuple[str, str], bool] = {}
        fallback_filename = row.get(um.COL_FILE)

        for case in cases:
            if not isinstance(case, dict):
                continue

            function_name = extract_function_name(case)
            if function_name is None:
                missing_function_cases += 1
                continue

            filename = extract_test_filename(case, fallback_filename)
            function_key = (filename, function_name)
            passed = status_is_passed(case.get("status"))
            event_functions[function_key] = (
                event_functions.get(function_key, False) or passed
            )

        event_id = (
            row.get(COL_EVENT_ID)
            if COL_EVENT_ID in attempts.columns
            else row_index
        )

        for (filename, function_name), has_passed_test in event_functions.items():
            records.append(
                {
                    um.COL_ACTOR: str(row[um.COL_ACTOR]),
                    "__event_id": event_id,
                    "__filename": filename,
                    "__function_name": function_name,
                    "__function_key": f"{filename}::{function_name}",
                    "__has_passed_test": has_passed_test,
                    code_state_col: row.get(code_state_col),
                }
            )

    if unparsed_test_events:
        out.warning(
            "%d Run.Test sans cas de test exploitable ont été ignorés",
            unparsed_test_events,
        )
    if missing_function_cases:
        out.warning(
            "%d cas de test sans nom de fonction exploitable ont été ignorés",
            missing_function_cases,
        )

    columns = [
        um.COL_ACTOR,
        "__event_id",
        "__filename",
        "__function_name",
        "__function_key",
        "__has_passed_test",
        code_state_col,
    ]
    return pd.DataFrame.from_records(records, columns=columns)


def calculate_function_coverage(
    actor_rows: pd.DataFrame,
    code_state_col: str = COL_CODE_STATE,
) -> tuple[int, int, int]:
    """Compte les fonctions traitées par un étudiant.

    Retourne ``(total, par_test_reussi, par_code_states_uniquement)``. Le
    troisième nombre exclut les fonctions qui ont déjà au moins un test réussi.
    """
    treated_count = 0
    treated_by_passed_test = 0
    treated_by_code_states_only = 0

    for _, function_rows in actor_rows.groupby("__function_key", sort=False):
        has_passed_test = bool(function_rows["__has_passed_test"].any())
        distinct_code_state_count = (
            function_rows[code_state_col]
            .dropna()
            .astype(str)
            .loc[lambda values: values.str.strip().ne("")]
            .nunique()
        )
        has_two_distinct_code_states = distinct_code_state_count >= 2

        if has_passed_test or has_two_distinct_code_states:
            treated_count += 1
            if has_passed_test:
                treated_by_passed_test += 1
            else:
                treated_by_code_states_only += 1

    return treated_count, treated_by_passed_test, treated_by_code_states_only


def main(
    read_path: str,
    write_path: str,
    code_state_col: str = COL_CODE_STATE,
) -> None:
    df = um.load_csv(read_path)

    required_cols = [
        um.COL_ACTOR,
        um.COL_VERB,
        um.COL_TESTS,
        code_state_col,
    ]
    if not um.check_columns(df, required_cols):
        sys.exit(1)

    # ``filename_infere`` est facultatif, car le chemin du fichier est aussi
    # normalement présent dans chacun des cas de test.
    actors = (
        df[um.COL_ACTOR]
        .astype("string")
        .dropna()
        .loc[lambda values: values.str.strip().ne("")]
        .unique()
        .tolist()
    )

    function_attempts = prepare_function_attempts(df, code_state_col)
    out.info(
        "%d étudiant(s), %d association(s) Run.Test/fonction exploitable(s)",
        len(actors),
        len(function_attempts),
    )

    metric_map: dict[str, int] = {}
    for actor in sorted(actors):
        actor_rows = function_attempts[
            function_attempts[um.COL_ACTOR] == str(actor)
        ]
        coverage, by_passed_test, by_code_states_only = (
            calculate_function_coverage(actor_rows, code_state_col)
        )

        metric_map[str(actor)] = coverage
        out.info(
            "  %s : %d fonction(s) traitée(s) "
            "(%d avec au moins un test réussi, "
            "%d par états de code distincts uniquement)",
            actor,
            coverage,
            by_passed_test,
            by_code_states_only,
        )

    um.write_metric(METRIC_NAME, metric_map, write_path)


if __name__ == "__main__":
    input_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/traces_20_sept_10_11.csv"
    )
    output_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "out/FunctionCoverage.csv"
    )
    code_state_column = sys.argv[3] if len(sys.argv) > 3 else COL_CODE_STATE

    main(input_path, output_path, code_state_col=code_state_column)
