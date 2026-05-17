# mean_test_score.py
import os
import sys
import logging
import pandas as pd

out = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def load_main_table(read_path: str) -> pd.DataFrame:
    """
    Charge MainTable depuis un chemin fichier ou un dossier.

    - Si read_path est un dossier: cherche MainTable.csv/xlsx/xls à l'intérieur
    - Supporte: .csv, .xlsx, .xls
    """
    if os.path.isdir(read_path):
        candidates = ["MainTable.csv", "MainTable.xlsx", "MainTable.xls"]
        for name in candidates:
            fp = os.path.join(read_path, name)
            if os.path.exists(fp):
                read_path = fp
                break
        else:
            raise FileNotFoundError(f"Aucun MainTable.csv/xlsx trouvé dans {read_path}")

    ext = os.path.splitext(read_path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(read_path)
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(read_path)
    raise ValueError(f"Extension non supportée: {ext} (attendu .csv/.xlsx/.xls)")


def check_attributes(df: pd.DataFrame, required: list[str]) -> bool:
    missing = [c for c in required if c not in df.columns]
    if missing:
        out.error(f"Colonnes manquantes: {missing}")
        return False
    return True


def calculate_metric_map(df: pd.DataFrame, metric_fn) -> dict:
    metric_map = {}
    for subject_id, session_table in df.groupby("SubjectID"):
        val = metric_fn(session_table)
        if val is not None and pd.notna(val):
            metric_map[subject_id] = val
    return metric_map


def write_metric_map(metric_name: str, metric_map: dict, write_path: str) -> None:
    os.makedirs(os.path.dirname(write_path) or ".", exist_ok=True)
    out_df = pd.DataFrame({
        "SubjectID": list(metric_map.keys()),
        metric_name: list(metric_map.values()),
    }).sort_values("SubjectID")
    out_df.to_csv(write_path, index=False)


def calculate_mean_test_score(session_table: pd.DataFrame) -> float | None:
    """
    Moyenne des scores des 'tests' pour un étudiant.

    Hypothèses raisonnables pour les traces type MainTable:
    - Les scores des tests sont portés par la colonne 'Score'
    - Les exécutions de tests sont souvent des événements 'Run.*' (ex: 'Run.Program')

    On calcule la moyenne des lignes:
    - EventType commence par 'Run' (fallback: toutes les lignes avec Score non nul)
    - Score convertible en numérique
    """
    # 1) Cas standard : événements de type Run.*
    run_mask = session_table["EventType"].astype(str).str.startswith("Run", na=False)
    tests = session_table[run_mask].copy()

    # 2) Fallback : si aucun Run.*, on prend toutes les lignes avec Score renseigné
    if tests.empty:
        tests = session_table[session_table["Score"].notna()].copy()

    if tests.empty:
        return None

    scores = pd.to_numeric(tests["Score"], errors="coerce").dropna()
    if scores.empty:
        return None

    return float(scores.mean())


if __name__ == "__main__":
    read_path = "./data"
    write_path = "./out/MeanTestScore.csv"

    if len(sys.argv) > 1:
        read_path = sys.argv[1]
    if len(sys.argv) > 2:
        write_path = sys.argv[2]

    main_table_df = load_main_table(read_path)
    if check_attributes(main_table_df, ["SubjectID", "EventType", "Score"]):
        metric_map = calculate_metric_map(main_table_df, calculate_mean_test_score)
        out.info(f"Computed MeanTestScore for {len(metric_map)} subjects")
        write_metric_map("MeanTestScore", metric_map, write_path)
