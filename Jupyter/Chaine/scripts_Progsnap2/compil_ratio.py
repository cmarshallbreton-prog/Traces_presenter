# compil_ratio.py
import sys
import logging

import utils
import data_filter

out = logging.getLogger()


def calculate_compile_ratio(session_table):
    """
    Calcule : compilations réussies / (compilations réussies + compilations échouées)
    sur la table déjà filtrée par data_filter, comme eq/red/watwin.
    """
    compiles = session_table[session_table["EventType"] == "Compile"]
    if len(compiles) == 0:
        return None

    results = compiles["Compile.Result"].dropna().astype(str)
    if len(results) == 0:
        return None

    success = int((results == "Success").sum())
    error = int((results == "Error").sum())
    total = success + error

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

    main_table_df = data_filter.load_main_table(read_path)
    checker = utils.check_attributes(main_table_df, ["SubjectID", "SessionID", "EventType", "Compile.Result"])
    if checker:
        metric_map = utils.calculate_metric_map(main_table_df, calculate_compile_ratio)
        out.info(metric_map)
        utils.write_metric_map("CompileSuccessRate", metric_map, write_path)
