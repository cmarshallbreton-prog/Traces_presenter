"""
Utilitaires partagés par les indicateurs Mirabelle.

Ces deux indicateurs (Error Quotient de Jadud et Repeated Error Density)
nécessitent de savoir si deux erreurs sont "identiques". Dans
scripts_Progsnap2 (eq.py / red.py), cette identité est déterminée par la
colonne CompileMessageType. Dans les traces Mirabelle, on ne dispose pas
d'un tel niveau de détail : on se base donc sur le champ 'verdict' de
chaque cas de test contenu dans la colonne 'tests' des évènements
Run.Test. Deux erreurs sont considérées comme identiques si elles sont
toutes les deux des FailedVerdict, ou toutes les deux des
ExceptionVerdict (voir ERROR_VERDICTS).

Une tentative (Run.Test) est traitée comme l'équivalent d'un évènement
Compile de scripts_Progsnap2 : elle peut produire zéro, une ou plusieurs
erreurs (une par cas de test en échec).
"""
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

VERB_TEST = "Run.Test"
COL_ACTOR = "actor"
COL_VERB = "verb"
COL_TESTS = "tests"
COL_TS = "timestamp.$date"
# Colonnes optionnelles utilisées pour segmenter les tentatives d'un même
# étudiant (par problème/fichier, par session, et par état du code).
COL_FILE = "filename_infere"
COL_SESSION = "session.id"
COL_CODESTATE = "P_codeState"
COL_ACTIVITY_SESSION = "__activity_session"
DEFAULT_SESSION_GAP_MINUTES = 5.0

# Verdicts considérés comme des erreurs (par opposition à Passed* qui
# signale un test réussi).
ERROR_VERDICTS = {"FailedVerdict", "ExceptionVerdict"}

REQUIRED_COLS = [COL_ACTOR, COL_VERB, COL_TESTS, COL_TS]


def parse_tests(raw) -> list[dict]:
    """Parse la colonne ``tests`` en conservant les traces échappées.

    Le corpus Mirabelle contient des représentations Python où certaines
    apostrophes internes sont doublement échappées (``\\'``). Elles rendent
    la chaîne invalide pour :func:`ast.literal_eval` alors que la structure
    sous-jacente est récupérable. On tente donc d'abord le parsing normal,
    puis un fallback *ciblé* qui ne déséchappe que ce motif connu.

    Une valeur réellement illisible est signalée dans les logs au lieu d'être
    silencieusement confondue avec un ``Run.Test`` sans cas de test.
    """
    if not isinstance(raw, str) or raw.strip().lower() in ("", "[]", "nan"):
        return []

    candidates = [raw]
    repaired = raw.replace("\\\\'", "\\'")
    if repaired != raw:
        candidates.append(repaired)

    for candidate in candidates:
        try:
            parsed = ast.literal_eval(candidate)
        except (ValueError, SyntaxError):
            continue
        if isinstance(parsed, list):
            return [case for case in parsed if isinstance(case, dict)]

    out.warning("Valeur 'tests' illisible (début) : %s", raw[:120])
    return []


def add_activity_session_ids(
    rows: pd.DataFrame,
    *,
    gap_minutes: float = DEFAULT_SESSION_GAP_MINUTES,
    output_col: str = COL_ACTIVITY_SESSION,
    timestamp_col: str = COL_TS,
) -> pd.DataFrame:
    """Ajoute un identifiant de session d'activité cohérent à Mirabelle.

    Une nouvelle session commence, pour un même étudiant, lorsque l'écart avec
    le ``Run.Test`` précédent est strictement supérieur à ``gap_minutes``.
    L'identifiant est local à l'étudiant et ne dépend pas de ``session.id`` du
    fichier source, dont la granularité est différente.
    """
    result = rows.copy()
    if result.empty:
        result[output_col] = pd.Series(dtype="Int64")
        return result
    if COL_ACTOR not in result.columns or timestamp_col not in result.columns:
        raise KeyError(f"Colonnes requises pour les sessions : {COL_ACTOR}, {timestamp_col}")

    helper_ts = "__activity_ts"
    helper_order = "__activity_order"
    result[helper_order] = range(len(result))
    if timestamp_col == "__timestamp" and pd.api.types.is_datetime64_any_dtype(result[timestamp_col]):
        result[helper_ts] = result[timestamp_col]
    else:
        result[helper_ts] = pd.to_datetime(result[timestamp_col], errors="coerce", utc=True)
    result = result.dropna(subset=[COL_ACTOR, helper_ts]).sort_values(
        [COL_ACTOR, helper_ts, helper_order], kind="mergesort"
    )

    session_ids = pd.Series(index=result.index, dtype="Int64")
    for _, actor_rows in result.groupby(COL_ACTOR, sort=False):
        gaps = actor_rows[helper_ts].diff().dt.total_seconds().div(60.0)
        starts = gaps.isna() | gaps.gt(float(gap_minutes))
        session_ids.loc[actor_rows.index] = starts.cumsum().astype("int64").to_numpy()

    result[output_col] = session_ids
    return result.drop(columns=[helper_ts, helper_order])


def error_categories(raw) -> frozenset:
    """
    Renvoie l'ensemble des catégories d'erreur ('FailedVerdict',
    'ExceptionVerdict') présentes parmi les cas de test d'un évènement
    Run.Test. Un ensemble vide signifie que l'évènement n'a produit
    aucune erreur (tous les cas de test sont passés, ou il n'y a aucun
    cas de test).

    Granularité GROSSIÈRE : deux erreurs sont "identiques" si elles ont
    le même verdict (voir error_quotient.py / repeated_error_density.py).
    """
    cases = parse_tests(raw)
    return frozenset(
        case.get("verdict")
        for case in cases
        if case.get("verdict") in ERROR_VERDICTS
    )


def error_message(case: dict):
    """
    Construit un identifiant textuel FIN pour un cas de test en échec,
    utilisé pour la granularité "message d'erreur" (voir
    error_quotient_message.py / repeated_error_density_message.py) :
    deux erreurs ayant le même verdict mais un contenu différent (par
    exemple ZeroDivisionError vs IndexError, ou deux échecs de test
    ayant renvoyé des valeurs incorrectes différentes) ne sont plus
    considérées comme identiques.

    - Pour une ExceptionVerdict, le champ 'details' contient la trace
      Python complète (chemin de fichier, numéro de ligne, code fautif,
      puis la ligne finale "NomException: message"). On ignore le
      chemin/numéro de ligne (qui changent d'un étudiant à l'autre et
      n'ont pas de sens à comparer) et on ne garde que cette dernière
      ligne, qui identifie à la fois le TYPE d'exception et son MESSAGE
      (ex: "ZeroDivisionError: division by zero").
    - Pour une FailedVerdict (le test s'exécute sans lever d'exception
      mais renvoie une valeur incorrecte), il n'existe pas de message
      d'erreur à proprement parler : l'identifiant fin retenu est donc
      le couple (valeur attendue, valeur obtenue), qui distingue deux
      échecs produisant des résultats erronés différents.
    - Retourne None si le cas de test n'est pas en erreur.

    Note : dans les données, le champ 'details' des ExceptionVerdict
    contient la séquence littérale de deux caractères backslash+n comme
    séparateur de ligne (et non un vrai retour à la ligne) ; c'est ce
    qu'on découpe ci-dessous.
    """
    verdict = case.get("verdict")
    if verdict not in ERROR_VERDICTS:
        return None

    if verdict == "ExceptionVerdict":
        details = case.get("details") or ""
        lines = [line.strip() for line in str(details).split("\\n") if line.strip()]
        if lines:
            return "ExceptionVerdict :: " + lines[-1]
        return "ExceptionVerdict :: (message indisponible)"

    # FailedVerdict
    expected = case.get("expected_result")
    obtained = case.get("details")
    return f"FailedVerdict :: attendu={expected!r} obtenu={obtained!r}"


def error_messages(raw) -> frozenset:
    """
    Équivalent de error_categories(), mais à la granularité fine du
    message d'erreur (voir error_message ci-dessus).
    """
    cases = parse_tests(raw)
    return frozenset(
        error_message(case)
        for case in cases
        if error_message(case) is not None
    )


def build_attempts(actor_rows: pd.DataFrame) -> pd.DataFrame:
    """
    Extrait, pour un étudiant donné, la suite ordonnée (par timestamp) de
    ses tentatives (évènements Run.Test), enrichie de deux colonnes
    alternatives décrivant les erreurs de chaque tentative :
      - 'error_categories' : granularité grossière (verdict seul,
        'FailedVerdict' / 'ExceptionVerdict') — voir error_quotient.py /
        repeated_error_density.py ;
      - 'error_messages' : granularité fine (contenu du message
        d'erreur) — voir error_quotient_message.py /
        repeated_error_density_message.py.
    Les deux sont calculées systématiquement (coût négligeable) afin que
    les quatre scripts puissent réutiliser la même table de tentatives.
    Une colonne booléenne 'has_error' est également ajoutée (identique
    quelle que soit la granularité : une tentative est en erreur dès
    qu'au moins un cas de test a échoué).
    """
    attempts = actor_rows[actor_rows[COL_VERB] == VERB_TEST].copy()
    if attempts.empty:
        return attempts

    attempts["_ts"] = pd.to_datetime(attempts[COL_TS], errors="coerce", utc=True)
    attempts = attempts.dropna(subset=["_ts"])
    attempts = add_activity_session_ids(attempts, timestamp_col="_ts")
    attempts = attempts.sort_values("_ts", kind="mergesort").reset_index(drop=True)
    attempts["error_categories"] = attempts[COL_TESTS].apply(error_categories)
    attempts["error_messages"] = attempts[COL_TESTS].apply(error_messages)
    attempts["has_error"] = attempts["error_categories"].apply(lambda s: len(s) > 0)
    return attempts


def get_segments_indexes(attempts: pd.DataFrame) -> list[list[int]]:
    """
    Découpe la suite ordonnée de tentatives d'un étudiant en segments, à
    la manière de get_segments_indexes dans scripts_Progsnap2/utils.py :
      - une tentative dont le code (P_codeState) n'a pas changé par
        rapport à la précédente est ignorée (l'étudiant a relancé les
        tests sans modifier son code) ;
      - un nouveau segment démarre dès que le problème
        (filename_infere) ou la session d’activité dérivée (pause > 5 min) change.
    Si les colonnes optionnelles de segmentation ne sont pas présentes
    dans le CSV, la contrainte correspondante est simplement ignorée
    (dégradation gracieuse).

    Retourne une liste de listes d'indices positionnels dans `attempts`.
    """
    n = len(attempts)
    if n == 0:
        return []

    has_codestate = COL_CODESTATE in attempts.columns
    seg_cols = [c for c in (COL_FILE, COL_ACTIVITY_SESSION) if c in attempts.columns]

    segments = []
    current_segment = [0]
    for i in range(1, n):
        # La frontière de segment doit être traitée AVANT le test du code
        # inchangé : le premier événement d'une nouvelle session/fichier ne
        # doit jamais être avalé parce que son code ressemble au précédent.
        changed_segment = False
        for col in seg_cols:
            prev_val = attempts[col].iloc[i - 1]
            curr_val = attempts[col].iloc[i]
            if pd.isna(prev_val) and pd.isna(curr_val):
                continue
            if (pd.isna(prev_val) != pd.isna(curr_val)) or prev_val != curr_val:
                changed_segment = True
                break

        if changed_segment:
            if current_segment:
                segments.append(current_segment)
            current_segment = [i]
            continue

        if has_codestate:
            prev_code = attempts[COL_CODESTATE].iloc[i - 1]
            curr_code = attempts[COL_CODESTATE].iloc[i]
            if pd.notna(prev_code) and pd.notna(curr_code) and prev_code == curr_code:
                continue

        current_segment.append(i)

    if len(current_segment) > 0:
        segments.append(current_segment)

    return segments


def extract_attempt_pairs(attempts: pd.DataFrame) -> list[list[int]]:
    """Renvoie la liste des paires d'indices de tentatives consécutives
    au sein de chaque segment (cf. extract_compile_pair_indexes de
    scripts_Progsnap2/utils.py)."""
    pairs = []
    for segment in get_segments_indexes(attempts):
        for i in range(1, len(segment)):
            pairs.append([segment[i - 1], segment[i]])
    return pairs


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
