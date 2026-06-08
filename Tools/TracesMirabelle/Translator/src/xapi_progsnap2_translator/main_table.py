from typing import Any, Iterable

from .code_states import compute_code_states_id, extract_code_state
from .link_table import get_anonymized_subject_id
from .types import ALLOWED_EVENT_TYPES, ERROR, MAIN_TABLE_FIELDS, MainRow, MainTableHandler, Statement, SUCCESS, TOOL_INSTANCES_DEFAULT
from .utils import (
    coerce_cell_text,
    extract_event_id,
    find_extension_value,
    get_event_type,
    get_object_extension,
    get_result_extension,
    get_server_timestamp,
    is_research_usable,
)


def extract_session_id(statement: Statement) -> str:
    """Retourne SessionID depuis context.extension /Session/ID."""

    context = statement.get("context")
    if not isinstance(context, dict):
        return ""
    extension = context.get("extension")
    if not isinstance(extension, dict):
        return ""
    value = find_extension_value(extension, "/Session/ID")
    return coerce_cell_text(value) if value is not None else ""


def extract_success(statement: Statement) -> bool | None:
    """Retourne result.success si présent, sinon None."""

    result = statement.get("result")
    if not isinstance(result, dict):
        return None
    success = result.get("success")
    return success if isinstance(success, bool) else None


def extract_output_error(statement: Statement) -> tuple[str, str]:
    """Retourne (stdout, stderr) depuis result.extension ou object.extension."""

    result_extension = get_result_extension(statement)
    object_extension = get_object_extension(statement)
    output_value = find_extension_value(result_extension, "/stdout", "/Stdout")
    if output_value is None:
        output_value = find_extension_value(object_extension, "/stdout", "/Stdout")
    error_value = find_extension_value(result_extension, "/stderr", "/Stderr")
    if error_value is None:
        error_value = find_extension_value(object_extension, "/stderr", "/Stderr")
    return coerce_cell_text(output_value), coerce_cell_text(error_value)


def extract_lineno(statement: Statement) -> str:
    """Retourne le numéro de ligne pour les événements de débogage."""

    extension = get_object_extension(statement)
    value = find_extension_value(extension, "/Lineno")
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    return coerce_cell_text(value)


def extract_run_test_data(statement: Statement) -> str:
    """Retourne les données de tests depuis object.extension /Tests."""

    extension = get_object_extension(statement)
    return coerce_cell_text(find_extension_value(extension, "/Tests"))


def extract_run_test_success(statement: Statement) -> bool | None:
    """Retourne le statut global d'un Run.Test si présent."""

    success = extract_success(statement)
    if success is not None:
        return success

    extension = get_object_extension(statement)
    status = find_extension_value(extension, "/Status")
    return status if isinstance(status, bool) else None


def extract_run_test_error(statement: Statement) -> str:
    """Retourne l'erreur associée à un Run.Test si présente."""

    extension = get_object_extension(statement)
    return coerce_cell_text(find_extension_value(extension, "/Error"))


def make_base_row(event_id: str, event_type: str, statement: Statement) -> MainRow:
    """Construit une ligne MainTable avec les champs communs."""

    code_state = extract_code_state(statement)
    code_state_id = compute_code_states_id(code_state)

    row: MainRow = {field: "" for field in MAIN_TABLE_FIELDS}
    row.update(
        {
            "EventID": str(event_id),
            "EventType": event_type,
            "SubjectID": get_anonymized_subject_id(statement),
            "ToolInstances": TOOL_INSTANCES_DEFAULT,
            "CodeStateID": code_state_id,
            "ServerTimestamp": get_server_timestamp(statement),
            "SessionID": extract_session_id(statement),
        }
    )
    return row


def fill_execution_result_fields(row: MainRow, statement: Statement) -> None:
    """Renseigne les colonnes ProgSnap2 d'exécution."""

    success = extract_success(statement)
    if success is None:
        return

    output_text, error_text = extract_output_error(statement)
    row["ExecutionResult"] = SUCCESS if success else ERROR
    row["ProgramOutput"] = output_text
    row["ProgramErrorOutput"] = "" if success else error_text


def handle_run_program(statement: Statement, event_id: str, event_type: str) -> MainRow:
    """Gère les événements Run.Program."""

    row = make_base_row(event_id, event_type, statement)
    fill_execution_result_fields(row, statement)
    return row


def handle_run_test(statement: Statement, event_id: str, event_type: str) -> MainRow:
    """Gère les événements Run.Test."""

    row = make_base_row(event_id, event_type, statement)
    row["X-RunTestData"] = extract_run_test_data(statement)
    success = extract_run_test_success(statement)
    if success is not None:
        row["ExecutionResult"] = SUCCESS if success else ERROR
    error = extract_run_test_error(statement)
    if error:
        row["ProgramErrorOutput"] = error
    return row


def handle_run_debugger(statement: Statement, event_id: str, event_type: str) -> MainRow:
    """Gère les anciens événements Run.Debugger, mappés vers Debug.Program."""

    row = make_base_row(event_id, event_type, statement)
    row["Lineno"] = extract_lineno(statement)
    fill_execution_result_fields(row, statement)
    return row


def handle_generic_event(statement: Statement, event_id: str, event_type: str) -> MainRow:
    """Gère les événements supportés sans colonnes spécialisées."""

    return make_base_row(event_id, event_type, statement)


MAIN_TABLE_HANDLERS: dict[str, MainTableHandler] = {
    "Run.Program": handle_run_program,
    "Run.Test": handle_run_test,
    "Debug.Program": handle_run_debugger,
}


def translate_statements_to_main_rows(statements: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    """Traduit des statements xAPI en lignes MainTable."""

    main_rows: list[dict[str, str]] = []

    for source_index, statement in enumerate(statements, start=1):
        if not is_research_usable(statement):
            continue

        event_type = get_event_type(statement)
        if event_type not in ALLOWED_EVENT_TYPES:
            continue

        handler = MAIN_TABLE_HANDLERS.get(event_type, handle_generic_event)
        event_id = extract_event_id(statement, source_index)
        main_rows.append(handler(statement, event_id, event_type))

    return main_rows
