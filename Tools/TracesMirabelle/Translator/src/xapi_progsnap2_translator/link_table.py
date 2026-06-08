from typing import Any, Iterable

from .types import ALLOWED_EVENT_TYPES, LinkRow, Statement
from .utils import (
    extract_primary_user_from_openid,
    extract_team_id_from_openid,
    get_event_type,
    is_research_usable,
    sha256_hex,
)


def get_actor_openid(statement: Statement) -> str:
    """Retourne actor.openid si présent."""

    actor = statement.get("actor")
    actor_openid = actor.get("openid") if isinstance(actor, dict) else ""
    return actor_openid if isinstance(actor_openid, str) else ""


def get_anonymized_subject_id(statement: Statement) -> str:
    """Retourne SubjectID anonymisé à partir de l'utilisateur principal."""

    user = extract_primary_user_from_openid(get_actor_openid(statement))
    return sha256_hex(user) if user else ""


def get_identifier(statement: Statement) -> str:
    """Retourne l'identifiant non anonymisé à placer dans la LinkTable."""

    return extract_primary_user_from_openid(get_actor_openid(statement))


def get_team_id(statement: Statement) -> str:
    """Retourne le groupe complet d'acteurs si l'openid représente un binôme."""

    return extract_team_id_from_openid(get_actor_openid(statement))


def translate_statements_to_link_rows(
    statements: Iterable[dict[str, Any]],
) -> list[LinkRow]:
    """Construit LinkTables/Subject.csv en dédupliquant les SubjectID."""

    seen: dict[str, dict[str, str]] = {}
    for statement in statements:
        if not is_research_usable(statement):
            continue

        event_type = get_event_type(statement)
        if event_type not in ALLOWED_EVENT_TYPES:
            continue

        subject_id = get_anonymized_subject_id(statement)
        identifier = get_identifier(statement)
        if not subject_id or not identifier:
            continue

        row = {"SubjectID": subject_id, "X-Identifier": identifier}
        team_id = get_team_id(statement)
        if team_id and team_id != identifier:
            row["X-TeamID"] = team_id

        seen.setdefault(subject_id, row)

    return list(seen.values())
