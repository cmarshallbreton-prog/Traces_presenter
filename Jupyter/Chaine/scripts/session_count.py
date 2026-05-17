# session_count.py
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


def calculate_session_count(session_table: pd.DataFrame, gap_minutes: float = 5.0) -> int:
    comp = session_table[session_table["EventType"] == "Compile"].copy()
    if comp.empty:
        return 0

    # On s'appuie sur ServerTimestamp; fallback sur Order si besoin
    if "ServerTimestamp" in comp.columns:
        comp["__t"] = pd.to_datetime(comp["ServerTimestamp"], errors="coerce", utc=True)
        comp = comp.sort_values(["__t", "Order"] if "Order" in comp.columns else ["__t"])
        times = comp["__t"].dropna()
        if len(times) >= 1:
            gaps = times.diff().dt.total_seconds().dropna()
            threshold = gap_minutes * 60.0
            return int(1 + (gaps > threshold).sum())

    # Fallback: si timestamps inutilisables, on considère 1 session si >=1 compile
    return 1


if __name__ == "__main__":
    read_path = "./data"
    write_path = "./out/SessionCount.csv"
    gap_minutes = 5.0

    if len(sys.argv) > 1:
        read_path = sys.argv[1]
    if len(sys.argv) > 2:
        write_path = sys.argv[2]
    if len(sys.argv) > 3:
        gap_minutes = float(sys.argv[3])

    main_table_df = load_main_table(read_path)
    if check_attributes(main_table_df, ["SubjectID", "EventType", "ServerTimestamp"]):
        metric_map = calculate_metric_map(
            main_table_df,
            lambda st: calculate_session_count(st, gap_minutes=gap_minutes)
        )
        out.info(f"Computed SessionCount for {len(metric_map)} subjects (gap={gap_minutes}min)")
        write_metric_map("SessionCount", metric_map, write_path)