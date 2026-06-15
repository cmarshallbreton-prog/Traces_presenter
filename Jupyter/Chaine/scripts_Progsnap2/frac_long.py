# frac_long.py
import sys
import logging

import pandas as pd

import utils
import data_filter

out = logging.getLogger()


def calculate_frac_long(session_table, gap_minutes=5.0):
    """
    Fraction de pauses longues entre compilations, calculée après le filtrage
    commun de data_filter, comme eq/red/watwin.
    """
    compiles = session_table[session_table["EventType"] == "Compile"].copy()
    if compiles.empty:
        return None

    compiles["__t"] = pd.to_datetime(compiles["ServerTimestamp"], errors="coerce", utc=True)
    compiles = compiles.dropna(subset=["__t"])
    if len(compiles) < 2:
        return None

    sort_cols = ["__t", "Order"] if "Order" in compiles.columns else ["__t"]
    compiles = compiles.sort_values(sort_cols)

    gaps = compiles["__t"].diff().dt.total_seconds().dropna()
    if len(gaps) == 0:
        return None

    threshold = gap_minutes * 60.0
    return float((gaps > threshold).sum() / len(gaps))


if __name__ == "__main__":
    read_path = "./data"
    write_path = "./out/FracLong.csv"
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
            lambda session: calculate_frac_long(session, gap_minutes=gap_minutes),
        )
        out.info(metric_map)
        utils.write_metric_map("FracLong", metric_map, write_path)
