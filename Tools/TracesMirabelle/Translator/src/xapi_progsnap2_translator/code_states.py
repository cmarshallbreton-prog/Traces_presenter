from typing import Any, Iterable

from .types import ALLOWED_EVENT_TYPES, CodeStateRow, Statement
from .utils import (
    coerce_cell_text,
    find_extension_value,
    get_event_type,
    get_object_extension,
    is_research_usable,
    normalize_newlines,
    sha256_hex,
)


def extract_code_state(statement: Statement) -> str:
    """Extrait le code source depuis object.extension /CodeState."""

    ext = get_object_extension(statement)
    return coerce_cell_text(find_extension_value(ext, "/CodeState"))


def compute_code_states_id(code_state: str) -> str:
    """Calcule l'identifiant stable d'un état de code."""

    if not code_state:
        return ""
    return sha256_hex(normalize_newlines(code_state))


def translate_statements_to_code_states_rows(
    statements: Iterable[dict[str, Any]],
) -> list[CodeStateRow]:
    """Construit CodeStates/CodeStates.csv en supprimant les doublons."""

    seen: dict[str, str] = {}
    for statement in statements:
        if not is_research_usable(statement):
            continue

        event_type = get_event_type(statement)
        if event_type not in ALLOWED_EVENT_TYPES:
            continue

        code_state = extract_code_state(statement)
        if not code_state:
            continue

        code_state_id = compute_code_states_id(code_state)
        if not code_state_id:
            continue

        seen.setdefault(code_state_id, code_state)

    return [{"CodeStateID": code_state_id, "Code": code_state} for code_state_id, code_state in seen.items()]
