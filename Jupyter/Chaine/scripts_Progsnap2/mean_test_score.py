"""Score moyen des événements d'exécution/test de ProgSnap2.

Dans chaque session filtrée, on sélectionne d'abord les événements dont le
type commence par ``Run`` ; si aucun n'existe, on utilise les lignes ayant un
``Score`` renseigné. La moyenne des scores de la session est ensuite moyennée
sur les sessions de l'étudiant.
"""

# mean_test_score.py
import sys
import logging

import pandas as pd

import utils
import data_filter

out = logging.getLogger()


def calculate_mean_test_score(session_table):
    """
    Moyenne des scores des tests sur la table déjà filtrée par data_filter,
    comme eq/red/watwin.
    """
    run_mask = session_table["EventType"].astype(str).str.startswith("Run", na=False)
    tests = session_table[run_mask].copy()

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

    main_table_df = data_filter.load_main_table(read_path)
    checker = utils.check_attributes(main_table_df, ["SubjectID", "SessionID", "EventType", "Score"])
    if checker:
        metric_map = utils.calculate_metric_map(main_table_df, calculate_mean_test_score)
        out.info(metric_map)
        utils.write_metric_map("MeanTestScore", metric_map, write_path)
