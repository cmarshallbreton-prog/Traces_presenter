# time_to_score1.py
import sys
import pandas as pd
import utils
import data_filter
import logging

out = logging.getLogger()

MAX_MINUTES_IF_NEVER = 60.0
SCORE_EPS = 1e-9


def calculate_minutes_to_score1(session_table, max_minutes_if_never=MAX_MINUTES_IF_NEVER):
    # Départ: 1re compile si possible, sinon 1er event daté
    compiles = session_table[session_table["EventType"] == "Compile"]
    comp_ts = pd.to_datetime(compiles["ServerTimestamp"], errors="coerce").dropna() if len(compiles) else pd.Series([], dtype="datetime64[ns]")

    if not comp_ts.empty:
        start_ts = comp_ts.min()
    else:
        all_ts = pd.to_datetime(session_table["ServerTimestamp"], errors="coerce").dropna()
        if all_ts.empty:
            return None
        start_ts = all_ts.min()

    runs = session_table[session_table["EventType"] == "Run.Program"].copy()
    if len(runs) == 0:
        return float(max_minutes_if_never)

    runs = runs[runs["Score"].notna()].copy()
    if len(runs) == 0:
        return float(max_minutes_if_never)

    runs["__ts"] = pd.to_datetime(runs["ServerTimestamp"], errors="coerce")
    runs = runs.dropna(subset=["__ts"])
    if runs.empty:
        return float(max_minutes_if_never)

    reached = runs[runs["Score"] >= (1.0 - SCORE_EPS)]
    if reached.empty:
        return float(max_minutes_if_never)

    first_success_ts = reached["__ts"].min()
    delta_min = (first_success_ts - start_ts).total_seconds() / 60.0
    return float(max(delta_min, 0.0))


if __name__ == "__main__":
    read_path = "./data"
    write_path = "./out/TimeToScore1.csv"

    if len(sys.argv) > 1:
        read_path = sys.argv[1]
    if len(sys.argv) > 2:
        write_path = sys.argv[2]

    main_table_df = data_filter.load_main_table(read_path)
    checker = utils.check_attributes(main_table_df, ["SubjectID", "EventType", "ServerTimestamp", "Score"])
    if checker:
        metric_map = utils.calculate_metric_map(
            main_table_df,
            lambda session: calculate_minutes_to_score1(session, MAX_MINUTES_IF_NEVER),
        )
        utils.write_metric_map("MinutesToScore1", metric_map, write_path)