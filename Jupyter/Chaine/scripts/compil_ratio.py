# compil_ratio.py
import os
import sys
import logging
import pandas as pd

out = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def load_main_table(read_path: str) -> pd.DataFrame:
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


def calculate_compile_ratio(session_table: pd.DataFrame) -> float | None:
    """
    Calcule : compilations réussies / (compilations réussies + compilations échouées)

    - On filtre EventType == "Compile"
    - On utilise la colonne "Compile.Result" (attendu: "Success" / "Error")
    - On ignore les autres valeurs (ex: "Warning", "Unknown", NaN)
    """
    comp = session_table[session_table["EventType"] == "Compile"].copy()
    if comp.empty:
        return None

    res = comp["Compile.Result"].dropna().astype(str)
    if res.empty:
        return None

    success = int((res == "Success").sum())
    error = int((res == "Error").sum())
    total = success + error

    # Si aucune compile n'est classable (pas de Success/Error), on ne renvoie rien
    if total == 0:
        return None

    return success / total


if __name__ == "__main__":
    read_path = "./data"
    write_path = "./out/CompileSuccessRate.csv"

    if len(sys.argv) > 1:
        read_path = sys.argv[1]
    if len(sys.argv) > 2:
        write_path = sys.argv[2]

    main_table_df = load_main_table(read_path)
    if check_attributes(main_table_df, ["SubjectID", "EventType", "Compile.Result"]):
        metric_map = calculate_metric_map(main_table_df, calculate_compile_ratio)
        out.info(f"Computed CompileSuccessRate for {len(metric_map)} subjects")
        write_metric_map("CompileSuccessRate", metric_map, write_path)