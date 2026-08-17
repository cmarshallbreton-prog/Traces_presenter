"""Nombre de compilations dans une session ProgSnap2 filtrée.

Le pipeline historique ``data_filter`` prépare les sessions, puis
``utils.calculate_metric_map`` applique cette fonction à chaque session et
retourne, pour chaque étudiant, la **moyenne du nombre de compilations par
session retenue**. Le comportement numérique historique est conservé.
"""

# compile_count.py
import sys
import logging

import utils
import data_filter

out = logging.getLogger()


def calculate_compile_count(session_table):
    return int((session_table["EventType"] == "Compile").sum())


if __name__ == "__main__":
    read_path = "./data"
    write_path = "./out/CompileCount.csv"

    if len(sys.argv) > 1:
        read_path = sys.argv[1]
    if len(sys.argv) > 2:
        write_path = sys.argv[2]

    main_table_df = data_filter.load_main_table(read_path)
    checker = utils.check_attributes(main_table_df, ["SubjectID", "SessionID", "EventType"])
    if checker:
        metric_map = utils.calculate_metric_map(main_table_df, calculate_compile_count)
        out.info(metric_map)
        utils.write_metric_map("CompileCount", metric_map, write_path)
