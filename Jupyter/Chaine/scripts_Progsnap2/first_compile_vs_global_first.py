# first_compile_vs_global_first.py
import sys
import pandas as pd
import utils
import data_filter
import logging

out = logging.getLogger()


def calculate_minutes_from_global_first_compile(session_table, global_first_compile_ts):
    compiles = session_table[session_table["EventType"] == "Compile"]
    if len(compiles) == 0:
        return None

    ts = pd.to_datetime(compiles["ServerTimestamp"], errors="coerce").dropna()
    if ts.empty:
        return None

    student_first_ts = ts.min()
    delta_min = (student_first_ts - global_first_compile_ts).total_seconds() / 60.0
    # Normalement >= 0, mais on garde robuste
    return float(max(delta_min, 0.0))


if __name__ == "__main__":
    read_path = "./data"
    write_path = "./out/FirstCompileVsGlobalFirst.csv"

    if len(sys.argv) > 1:
        read_path = sys.argv[1]
    if len(sys.argv) > 2:
        write_path = sys.argv[2]

    main_table_df = data_filter.load_main_table(read_path)
    checker = utils.check_attributes(main_table_df, ["SubjectID", "EventType", "ServerTimestamp"])
    if not checker:
        sys.exit(1)

    all_compiles = main_table_df[main_table_df["EventType"] == "Compile"].copy()
    all_compiles["__ts"] = pd.to_datetime(all_compiles["ServerTimestamp"], errors="coerce")
    all_compiles = all_compiles.dropna(subset=["__ts"])

    if all_compiles.empty:
        out.warning("Aucun événement 'Compile' avec timestamp valide dans le fichier.")
        sys.exit(0)

    global_first_compile_ts = all_compiles["__ts"].min()

    metric_map = utils.calculate_metric_map(
        main_table_df,
        lambda session: calculate_minutes_from_global_first_compile(session, global_first_compile_ts),
    )

    utils.write_metric_map("MinutesFromGlobalFirstCompile", metric_map, write_path)