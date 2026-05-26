# session_count.py
import sys
import logging

import pandas as pd

import utils
import data_filter

out = logging.getLogger()


def calculate_session_count(session_table, gap_minutes=5.0):
    """
    Nombre de sous-sessions de compilation, calculé après le filtrage commun
    de data_filter, comme eq/red/watwin.
    """
    compiles = session_table[session_table["EventType"] == "Compile"].copy()
    if compiles.empty:
        return None

    compiles["__t"] = pd.to_datetime(compiles["ServerTimestamp"], errors="coerce", utc=True)
    compiles = compiles.dropna(subset=["__t"])
    if compiles.empty:
        return None

    sort_cols = ["__t", "Order"] if "Order" in compiles.columns else ["__t"]
    compiles = compiles.sort_values(sort_cols)

    gaps = compiles["__t"].diff().dt.total_seconds().dropna()
    threshold = gap_minutes * 60.0
    return int(1 + (gaps > threshold).sum())


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

    main_table_df = data_filter.load_main_table(read_path)
    checker = utils.check_attributes(main_table_df, ["SubjectID", "SessionID", "EventType", "ServerTimestamp"])
    if checker:
        metric_map = utils.calculate_metric_map(
            main_table_df,
            lambda session: calculate_session_count(session, gap_minutes=gap_minutes),
        )
        out.info(metric_map)
        utils.write_metric_map("SessionCount", metric_map, write_path)
