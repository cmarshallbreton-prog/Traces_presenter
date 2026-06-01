#!/usr/bin/env python3
"""
Conversion très simple de traces JSON xAPI vers un MainTable.csv ProgSnap2
ne contenant que des événements de compilation.

Hypothèse pour les traces Python/Thonny : chaque Run.Program ou Run.test
correspond à une tentative de compilation du code courant. On compile le
CodeState avec compile(..., 'exec') pour savoir si la compilation Python
réussit. En cas de SyntaxError/IndentationError/TabError, on ajoute aussi
une ligne enfant Compile.Error.

Usage :
    python convert_compile_main_only.py traces250102.zip out_250102
    python convert_compile_main_only.py traces260105.zip out_260105

Le résultat est écrit dans out_*/MainTable.csv.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, Iterable, Optional, Tuple
import zipfile


COLUMNS = [
    "SubjectID",
    "ToolInstances",
    "ServerTimestamp",
    "ServerTimezone",
    "CourseID",
    "AssignmentID",
    "ProblemID",
    "CodeStateID",
    "IsEventOrderingConsistent",
    "EventType",
    "Score",
    "Compile.Result",
    "CompileMessageType",
    "CompileMessageData",
    "EventID",
    "Order",
    "ParentEventID",
]

DEFAULT_COMPILE_EVENTS = {"Run.Program", "Run.test"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def hash_subject(openid: str, salt: str = "") -> str:
    return sha256_text(salt + openid) if openid else ""


def short_event_type(event: Dict[str, Any]) -> str:
    verb_id = (((event.get("verb") or {}).get("id")) or "")
    return verb_id.rsplit("/", 1)[-1]


def date_value(value: Any) -> str:
    """Convertit {'$date': '...Z'} en timestamp proche de l'exemple fourni."""
    if isinstance(value, dict):
        value = value.get("$date", "")
    if not value:
        return ""
    s = str(value)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        # Le fichier exemple utilise une timezone séparée, donc on retire +00:00.
        return dt.replace(tzinfo=None).isoformat(timespec="seconds")
    except ValueError:
        return s


def oid_value(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("$oid", ""))
    return str(value or "")


def extension(event: Dict[str, Any], section: str) -> Dict[str, Any]:
    obj = event.get(section) or {}
    return (obj.get("extension") or {}) if isinstance(obj, dict) else {}


def first_ext_value(ext: Dict[str, Any], suffix: str, default: str = "") -> Any:
    for key, value in ext.items():
        if key.endswith(suffix):
            return value
    return default


def get_code_state(event: Dict[str, Any], include_commands: bool = False) -> str:
    obj_ext = extension(event, "object")

    # Les traces utilisent surtout .../Program/CodeState.
    for suffix in ("/Program/CodeState", "/File/CodeState", "/CodeState"):
        value = first_ext_value(obj_ext, suffix, None)
        if value is not None:
            return str(value)

    if include_commands:
        cmd = first_ext_value(obj_ext, "/Command/CommandRan", "")
        return str(cmd or "")

    return ""


def get_filename(event: Dict[str, Any]) -> str:
    obj_ext = extension(event, "object")
    value = first_ext_value(obj_ext, "/File/Filename", "")
    if value:
        return str(value)

    # Parfois le nom est caché dans une commande du type "%Run fichier.py".
    command = str(first_ext_value(obj_ext, "/Command/CommandRan", "") or "")
    parts = command.strip().split()
    if len(parts) >= 2 and parts[0].lower() in {"%run", "%debug"}:
        # Exemples à ignorer : "%Run -c $EDITOR_CONTENT".
        candidate = parts[1]
        if candidate != "-c" and "$EDITOR_CONTENT" not in candidate:
            return candidate
    return ""


def get_stderr(event: Dict[str, Any]) -> str:
    result_ext = extension(event, "result")
    return str(first_ext_value(result_ext, "/Command/stderr", "") or "")


def compile_python(code: str, filename: str = "<student_code>") -> Tuple[str, str, str]:
    """Renvoie (Compile.Result, CompileMessageType, CompileMessageData)."""
    if not code:
        return "Success", "", ""

    try:
        # Certains codes étudiants peuvent émettre des SyntaxWarning à la compilation.
        # On les ignore ici pour éviter de polluer la sortie du script.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            compile(code, filename or "<student_code>", "exec")
        return "Success", "", ""
    except SyntaxError as err:
        message_type = err.__class__.__name__
        bits = []
        if err.lineno is not None:
            bits.append(f"line {err.lineno}")
        if err.offset is not None:
            bits.append(f"col {err.offset}")
        if err.msg:
            bits.append(err.msg)
        if err.text:
            bits.append(err.text.strip())
        return "Error", message_type, ": ".join(bits)


def classify_compilation(event: Dict[str, Any], code: str, filename: str) -> Tuple[str, str, str]:
    """Classe l'événement comme compilation réussie ou erreur de compilation."""
    result, msg_type, msg_data = compile_python(code, filename)
    if result == "Error":
        return result, msg_type, msg_data

    # Filet de sécurité : si le CodeState manque mais stderr indique une erreur
    # de syntaxe Python, on la garde comme Compile.Error.
    stderr = get_stderr(event)
    for name in ("SyntaxError", "IndentationError", "TabError"):
        if name in stderr:
            first_line = next((line.strip() for line in stderr.splitlines() if name in line), "")
            return "Error", name, first_line or stderr.strip()[:500]

    return "Success", "", ""


def iter_json_array_objects(stream: BinaryIO, chunk_size: int = 1024 * 1024) -> Iterable[Dict[str, Any]]:
    """
    Lit un très gros JSON de la forme [ {...}, {...}, ... ] sans tout charger
    en mémoire. Version volontairement simple : elle découpe les objets au
    niveau des accolades, en tenant compte des chaînes JSON.
    """
    decoder = json.JSONDecoder()
    buf = ""
    started = False
    depth = 0
    in_string = False
    escape = False

    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        text = chunk.decode("utf-8", errors="replace")

        for ch in text:
            if not started:
                if ch == "{":
                    started = True
                    depth = 1
                    in_string = False
                    escape = False
                    buf = "{"
                continue

            buf += ch

            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        yield decoder.decode(buf)
                        started = False
                        buf = ""


def open_trace(path: Path):
    """Ouvre un .zip contenant un JSON unique, ou un .json direct."""
    if path.suffix.lower() == ".zip":
        zf = zipfile.ZipFile(path)
        names = [n for n in zf.namelist() if not n.endswith("/")]
        if len(names) != 1:
            raise ValueError(f"Le ZIP doit contenir un seul fichier JSON, trouvé : {names}")
        return zf, zf.open(names[0], "r")
    return None, path.open("rb")


def output_csv_path(output: Path) -> Path:
    if output.suffix.lower() == ".csv":
        output.parent.mkdir(parents=True, exist_ok=True)
        return output
    output.mkdir(parents=True, exist_ok=True)
    return output / "MainTable.csv"


def convert(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    csv_path = output_csv_path(Path(args.output))

    compile_event_types = set(DEFAULT_COMPILE_EVENTS)
    if args.include_commands:
        compile_event_types.add("Run.Command")

    event_id = args.first_event_id
    kept = 0
    errors = 0
    seen = 0

    zip_handle, stream = open_trace(input_path)
    try:
        with stream, csv_path.open("w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=COLUMNS)
            writer.writeheader()

            for event in iter_json_array_objects(stream):
                seen += 1
                if args.limit and seen > args.limit:
                    break

                if short_event_type(event) not in compile_event_types:
                    continue

                openid = str(((event.get("actor") or {}).get("openid")) or "")
                filename = get_filename(event)
                code = get_code_state(event, include_commands=args.include_commands)
                compile_result, msg_type, msg_data = classify_compilation(event, code, filename)

                subject_id = openid if args.keep_pii else hash_subject(openid, args.salt)
                clean_filename = filename.strip("\'\"") if filename else ""
                problem_id = Path(clean_filename).stem if clean_filename else ""
                code_state_id = sha256_text(code) if code else ""
                timestamp = date_value(event.get("timestamp"))

                compile_id = str(event_id)
                base = {
                    "SubjectID": subject_id,
                    "ToolInstances": args.tool_instances,
                    "ServerTimestamp": timestamp,
                    "ServerTimezone": args.server_timezone,
                    "CourseID": args.course_id,
                    "AssignmentID": args.assignment_id,
                    "ProblemID": problem_id,
                    "CodeStateID": code_state_id,
                    "IsEventOrderingConsistent": "True",
                    "Score": "",
                    "Order": str(event_id),
                }

                writer.writerow({
                    **base,
                    "EventType": "Compile",
                    "Compile.Result": compile_result,
                    "CompileMessageType": "",
                    "CompileMessageData": "",
                    "EventID": compile_id,
                    "ParentEventID": "",
                })
                event_id += 1
                kept += 1

                if compile_result == "Error":
                    writer.writerow({
                        **base,
                        "EventType": "Compile.Error",
                        "Compile.Result": "",
                        "CompileMessageType": msg_type,
                        "CompileMessageData": msg_data,
                        "EventID": str(event_id),
                        "Order": str(event_id),
                        "ParentEventID": compile_id,
                    })
                    event_id += 1
                    errors += 1
    finally:
        if zip_handle is not None:
            zip_handle.close()

    print(f"OK: {csv_path}")
    print(f"Événements lus: {seen}")
    print(f"Lignes Compile: {kept}")
    print(f"Lignes Compile.Error: {errors}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convertit des traces xAPI Python/Thonny en MainTable.csv ProgSnap2 minimal, compilation seulement."
    )
    parser.add_argument("input", help="Trace .zip contenant un JSON unique, ou fichier .json")
    parser.add_argument("output", help="Dossier de sortie, ou chemin direct vers MainTable.csv")
    parser.add_argument("--course-id", default="", help="Valeur CourseID à écrire dans le CSV")
    parser.add_argument("--assignment-id", default="", help="Valeur AssignmentID à écrire dans le CSV")
    parser.add_argument("--tool-instances", default="Python; Thonny", help="Valeur ToolInstances")
    parser.add_argument("--server-timezone", default="0", help="Valeur ServerTimezone")
    parser.add_argument("--salt", default="", help="Sel optionnel pour pseudonymiser SubjectID")
    parser.add_argument("--keep-pii", action="store_true", help="Garde les openid originaux au lieu de les hacher")
    parser.add_argument("--include-commands", action="store_true", help="Inclut aussi Run.Command")
    parser.add_argument("--first-event-id", type=int, default=1, help="Premier EventID généré")
    parser.add_argument("--limit", type=int, default=0, help="Limite de lecture pour tester rapidement")
    args = parser.parse_args()
    convert(args)


if __name__ == "__main__":
    main()
