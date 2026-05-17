# compile_span_per_student.py
import sys
import pandas as pd
import utils
import data_filter
import logging

out = logging.getLogger()


def calculate_compile_span_minutes(session_table):
    compiles = session_table[session_table["EventType"] == "Compile"]
    if len(compiles) == 0:
        return None

    ts = pd.to_datetime(compiles["ServerTimestamp"], errors="coerce").dropna()
    if ts.empty:
        return None

    span_min = (ts.max() - ts.min()).total_seconds() / 60.0
    return float(max(span_min, 0.0))


if __name__ == "__main__":
    read_path = "./data"
    write_path = "./out/CompileSpan.csv"

    if len(sys.argv) > 1:
        read_path = sys.argv[1]
    if len(sys.argv) > 2:
        write_path = sys.argv[2]

    main_table_df = data_filter.load_main_table(read_path)
    checker = utils.check_attributes(main_table_df, ["SubjectID", "EventType", "ServerTimestamp"])
    if checker:
        metric_map = utils.calculate_metric_map(main_table_df, calculate_compile_span_minutes)
        utils.write_metric_map("CompileSpanMinutes", metric_map, write_path)