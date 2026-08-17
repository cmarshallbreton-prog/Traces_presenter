"""Prétraitement historique des données ProgSnap2.

Ce module est partagé par les scripts ProgSnap2. Il charge ``MainTable.csv``,
construit/filtre les sessions puis retourne la table utilisée par les métriques.
Le seuil de session est exprimé explicitement en minutes afin d'éviter le
mélange historique secondes/minutes.
"""

# Table 1: Basic data set statistics System
# For each dataset, output: 1) System, 2) Course, 3) Language, 4) Students number, 5) Exercises(in # Sets), 6)
# Compilation events(% with error)
# What will be generated in this script: 1) System, 3) Language, 4) Students number, 5) Exercises, 6) Compilation events
# Table 2: Per-session data set statistics Dataset
# For each dataset, output: 1) Dataset, 2) Gap Time - Min Sessions, 3) Students number,
# 4) Compilation Events(% of total), 5) Sessions
# What will be generated in this script: 1) Dataset, 2) Gap Time- Min Sessions, 3) Students number,
# 4) Compilation Events(% of total), 5) Sessions
# Required format of input dataset: ProgSnap2

import pandas as pd
import numpy as np
import datetime
import sys
import os
import csv
import pathlib
import utils
import logging
import re

GAP_TIME = 20.0  # minutes (1200 secondes)
MIN_SESSIONS_Z = -2
MIN_COMPILES = 4
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

CACHE_VERSION = '2026.08.17.B'
CACHE_TABLE_NAME = "MainTable_filtered_" + CACHE_VERSION + ".csv"

out = logging.getLogger()


def get_valid_filename(s):
    """
    Return the given string converted to a string that can be used for a clean
    filename. Remove leading and trailing spaces; convert other spaces to
    underscores; and remove anything that is not an alphanumeric, dash,
    underscore, or dot.
    >>> get_valid_filename("john's portrait in 2004.jpg")
    'johns_portrait_in_2004.jpg'
    """
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)


def get_cache_table_path(data_dir):
    return "cache/" + get_valid_filename(data_dir) + "/" + CACHE_TABLE_NAME


def assign_session_ids(main_table_df, gap_time=GAP_TIME):
    if "SessionID" in main_table_df:
        return main_table_df

    out.info("Assigning session IDs (gap > %.1f min):", gap_time)
    timestamp_field = next(
        (tsf for tsf in ("ServerTimestamp", "ClientTimestamp") if tsf in main_table_df.columns),
        None,
    )
    if timestamp_field is None:
        raise ValueError("Aucune colonne ServerTimestamp/ClientTimestamp disponible")

    main_table_df.sort_values(['SubjectID', 'Order'], inplace=True)

    subject_id = None
    session_id = 0
    session_ids = []
    timestamps = pd.to_datetime(main_table_df[timestamp_field], errors="raise")

    subject_changes = 0
    last_timestamp = None
    for i, timestamp in enumerate(timestamps):
        current_subject = main_table_df["SubjectID"].iloc[i]
        if subject_id != current_subject:
            session_id += 1
            subject_id = current_subject
            subject_changes += 1
        elif last_timestamp is not None:
            gap_minutes = (timestamp - last_timestamp).total_seconds() / 60.0
            if gap_minutes > gap_time:
                session_id += 1

        # L'événement qui suit la pause appartient à la NOUVELLE session.
        session_ids.append(session_id)
        last_timestamp = timestamp
        utils.print_progress_bar(i + 1, len(main_table_df))

    main_table_df["SessionID"] = session_ids

    out.info("Subjects: " + str(subject_changes))
    out.info("Assigned %d unique sessionIDs" % session_id)

    main_table_df.sort_values(['Order'], inplace=True)
    return main_table_df


def filter_dataset(main_table_df, gap_time=GAP_TIME, min_compiles=MIN_COMPILES, min_sessions_z=MIN_SESSIONS_Z):
    main_table_df = assign_session_ids(main_table_df, gap_time)
    n_students = len(set(main_table_df["SubjectID"]))
    n_sessions = len(set(main_table_df["SessionID"]))

    out.info("Filtering sessions...")
    compile_sessions = main_table_df[main_table_df["EventType"] == "Compile"]["SessionID"]
    compiles_count_map = {session_id: np.sum(compile_sessions == session_id)
                          for session_id in set(main_table_df["SessionID"])}
    out.debug("Compiles count map: %s" % compiles_count_map)

    if not compiles_count_map:
        out.warning("Aucune session disponible après attribution des SessionID")
        return main_table_df.iloc[0:0].copy()
    mean_compiles = np.mean(list(compiles_count_map.values()))
    sd_compiles = np.std(list(compiles_count_map.values()))
    session_to_keep = [session_id for session_id in compiles_count_map.keys()
                       # if (compiles_count_map[session_id] - mean_compiles) / sd_compiles >= min_compiles]
                       if compiles_count_map[session_id] >= min_compiles]

    main_table_df = main_table_df[main_table_df["SessionID"].isin(session_to_keep)]
    out.info("Dropping %d sessions with < %.02f compiles (M=%.02f and SD=%.02f), removing %s students" %
            (n_sessions - len(session_to_keep), min_compiles, mean_compiles, sd_compiles,
             n_students - len(set(main_table_df["SubjectID"]))))

    out.info("Filtering students...")
    session_count_map = {subject_id: len(set(main_table_df[main_table_df["SubjectID"] == subject_id]["SessionID"]))
                         for subject_id in set(main_table_df["SubjectID"])}
    out.debug("Session count map: %s" % session_count_map)
    if not session_count_map:
        out.warning("Aucun étudiant ne possède de session avec au moins %d compilations", min_compiles)
        return main_table_df.iloc[0:0].copy()
    mean_sessions = np.mean(list(session_count_map.values()))
    sd_sessions = np.std(list(session_count_map.values()))
    if sd_sessions == 0:
        sd_sessions = 1

    students_to_keep = [subject_id for subject_id in session_count_map.keys()
                        if (session_count_map[subject_id] - mean_sessions) / sd_sessions >= min_sessions_z]

    out.info("Dropping %d students with with z-score < %.02f for sessions (M=%.02f and SD=%.02f)" %
            (len(session_count_map) - len(students_to_keep), min_sessions_z, mean_sessions, sd_sessions))

    main_table_df = main_table_df[main_table_df["SubjectID"].isin(students_to_keep)]

    return main_table_df


def get_table_1(main_table_df):
    # Calculate Table 1
    # We assume the dataset contains "Compile" and "Compile.Error" in EventType attribute
    # For the dataset which uses Python as programming language, we assume that any error reported by Python results in
    # a "Compilation Failure"
    # We assume one set contains one question
    # Get 1) and 3)
    if 'ToolInstances' in main_table_df.columns:
        tool_instances_arr = main_table_df["ToolInstances"].iloc[0].split(';')
        system = tool_instances_arr[0]
        if len(tool_instances_arr) > 1:
            language = tool_instances_arr[1]
        else:
            language = 'N/A'
    else:
        system = 'N/A'
        language = 'N/A'
    # Get 4) and 5)
    students_num = len(main_table_df['SubjectID'].unique().tolist())

    exercises_num = 0
    for pid in ['ProblemID', 'AssignmentID']:
        if pid in main_table_df:
            exercises_num = len(main_table_df[pid].dropna().unique().tolist())
            break

    sets_num = exercises_num
    # Get 6)
    compiles = main_table_df[main_table_df["EventType"] == "Compile"]
    compile_events = len(compiles)

    compile_errors = len(set(main_table_df[main_table_df["EventType"] == "Compile.Error"]["ParentEventID"]))
    perc_w_error = '{:.1%}'.format(compile_errors / compile_events) if compile_events else 'N/A'

    sessions_per_student = np.mean([
        len(set(main_table_df[main_table_df['SubjectID'] == subject_id]['SessionID']))
        for subject_id in set(main_table_df['SubjectID'])
    ])

    return [system, language, students_num, exercises_num, sets_num, compile_events, perc_w_error,
            sessions_per_student, len(main_table_df)]


def get_table_2(main_table_df):
    # Calculate Table 2
    # We assume the dataset contains "Compile" and "Compile.Error" in EventType attribute
    # For the dataset which uses Python as programming languge, we assume that any error reported by Python results in
    # a "Compilation Failure"
    # We assume each session contains one exercise

    # Get 1)
    if 'ToolInstances' in main_table_df.columns:
        tool_instances_arr = main_table_df["ToolInstances"].iloc[0].split(';')
        system = tool_instances_arr[0]
        if len(tool_instances_arr) > 1:
            language = tool_instances_arr[1]
        else:
            language = 'N/A'
    else:
        system = 'N/A'
        language = 'N/A'
    dataset_name = system + '(' + language + ')'

    # Get 3), 4), 5)
    compiles = main_table_df[main_table_df["EventType"] == "Compile"]
    total_compilation_event = len(compiles)
    main_table_df = filter_dataset(main_table_df, GAP_TIME, MIN_COMPILES, MIN_SESSIONS_Z)
    compilation_event = len(main_table_df[main_table_df["EventType"] == "Compile"])
    perc_of_total = '{:.1%}'.format(compilation_event/total_compilation_event) if total_compilation_event else 'N/A'

    sessions = len(main_table_df['SessionID'].unique().tolist())
    students = len(main_table_df['SubjectID'].unique().tolist())

    return dataset_name, GAP_TIME, MIN_SESSIONS_Z, students, compilation_event, perc_of_total, sessions


def load_main_table(read_dir, filter=True, from_cache=True):
    table_path = get_cache_table_path(read_dir)
    if filter and from_cache and os.path.exists(table_path):
        out.info("Loading from cached file: %s" % table_path)
        return pd.read_csv(table_path)

    main_table_df = pd.read_csv(os.path.join(read_dir, "MainTable.csv"))
    if filter:
        main_table_df = filter_dataset(main_table_df)
    return main_table_df


if __name__ == "__main__":
    read_path = "./data"
    write_dir = "./out"

    if len(sys.argv) > 1:
        read_path = sys.argv[1]
    if len(sys.argv) > 2:
        write_dir = sys.argv[2]

    main_table = pd.read_csv(os.path.join(read_path, "MainTable.csv"))

    # subjects = list(set(main_table['SubjectID']))[0:60]
    # main_table = main_table[main_table['SubjectID'].isin(subjects)].copy()

    checker = utils.check_attributes(main_table, ["SubjectID", ["ProblemID", "AssignmentID"], "EventType",
                                                  "CodeStateID", ["ClientTimestamp", "ServerTimestamp"]])
    if checker:
        main_table = assign_session_ids(main_table)
        table_1 = get_table_1(main_table)
        out.info(table_1)

        main_table = filter_dataset(main_table)
        table_2 = get_table_1(main_table)
        out.info(table_2)

        table_path = get_cache_table_path(read_path)
        pathlib.Path(table_path).parent.mkdir(parents=True, exist_ok=True)
        main_table.to_csv(table_path, index=False)

        pathlib.Path(write_dir).mkdir(parents=True, exist_ok=True)
        with open(os.path.join(write_dir, 'stats.csv'), 'w', newline='') as csvfile:
            obj = csv.writer(csvfile)
            obj.writerow(
                ['Filtered', 'System', 'Language', 'Students', 'Exercises', 'in # Sets', 'Compilation Events',
                 '% with Error', 'Sessions per Student', 'Total Events'])
            for name, table in {'No': table_1, 'Yes': table_2}.items():
                obj.writerow([name] + table)

        # csvfile2 = open(os.path.join(write_dir, 'table_2_Peterson2015.csv'), 'w', newline='')
        # obj = csv.writer(csvfile2)
        # obj.writerow(
        #     ['Dataset', 'Gap Time', 'Min Sessions', 'Students', 'Compilation Events', '% of Total', 'Sessions'])
        # obj.writerow(table_2)
        # csvfile2.close()


