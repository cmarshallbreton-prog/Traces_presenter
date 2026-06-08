import hashlib
import json
from typing import Any

from .types import PROGSNAP_EVENT_TYPE_MAP, Statement


def sha256_hex(text: str) -> str:
    """Calcule un SHA256 hexadécimal stable."""

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_event_type(statement: Statement) -> str:
    """Retourne le type d'événement ProgSnap2 canonique depuis verb.id."""

    verb = statement.get("verb")
    verb_id = verb.get("id") if isinstance(verb, dict) else ""
    if not isinstance(verb_id, str) or not verb_id:
        return ""
    raw_event_type = verb_id.rsplit("/", 1)[-1]
    return PROGSNAP_EVENT_TYPE_MAP.get(raw_event_type, raw_event_type)


def extract_primary_user_from_openid(actor_openid: str) -> str:
    """Extrait l'identifiant principal depuis actor.openid."""

    if not actor_openid:
        return ""

    marker = "/users/"
    if marker in actor_openid:
        actor_openid = actor_openid.split(marker, 1)[1]

    actor_openid = actor_openid.strip("/")
    if not actor_openid:
        return ""

    return actor_openid.split("/", 1)[0]


def extract_team_id_from_openid(actor_openid: str) -> str:
    """Retourne tous les identifiants placés après /users/ pour tracer les binômes."""

    if not actor_openid:
        return ""
    marker = "/users/"
    if marker in actor_openid:
        actor_openid = actor_openid.split(marker, 1)[1]
    return actor_openid.strip("/")


def coerce_xapi_date(value: Any) -> str:
    """Convertit une date xAPI/MongoDB en chaîne ISO exploitable en CSV."""

    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        mongo_date = value.get("$date")
        if isinstance(mongo_date, str):
            return mongo_date
    return ""


def get_server_timestamp(statement: Statement) -> str:
    """Retourne timestamp, ou stored si timestamp est absent."""

    return coerce_xapi_date(statement.get("timestamp")) or coerce_xapi_date(statement.get("stored"))


def is_research_usable(statement: Statement) -> bool:
    """Exclut uniquement les statements explicitement marqués research_usage=false."""

    return statement.get("research_usage") is not False


def extract_event_id(statement: Statement, fallback_index: int) -> str:
    """Retourne un EventID stable, de préférence depuis _id.$oid."""

    raw_id = statement.get("_id")
    if isinstance(raw_id, dict):
        oid = raw_id.get("$oid")
        if isinstance(oid, str) and oid:
            return oid
    if isinstance(raw_id, str) and raw_id:
        return raw_id
    statement_id = statement.get("id")
    if isinstance(statement_id, str) and statement_id:
        return statement_id
    return str(fallback_index)


def get_object_extension(statement: Statement) -> dict[str, Any]:
    """Retourne object.extension si présent et bien typé."""

    obj = statement.get("object")
    if not isinstance(obj, dict):
        return {}
    ext = obj.get("extension")
    return ext if isinstance(ext, dict) else {}


def get_result_extension(statement: Statement) -> dict[str, Any]:
    """Retourne result.extension si présent et bien typé."""

    res = statement.get("result")
    if not isinstance(res, dict):
        return {}
    ext = res.get("extension")
    return ext if isinstance(ext, dict) else {}


def find_extension_value(extension: dict[str, Any], *suffixes: str, ignore_case: bool = True) -> Any:
    """Trouve une valeur d'extension via un ou plusieurs suffixes d'URI."""

    normalized_suffixes = [suffix.lower() if ignore_case else suffix for suffix in suffixes]

    for key, value in extension.items():
        if not isinstance(key, str):
            continue
        candidate = key.lower() if ignore_case else key
        if any(candidate.endswith(suffix) for suffix in normalized_suffixes):
            return value
    return None


def normalize_newlines(text: str) -> str:
    """Normalise les fins de ligne pour un hash stable."""

    return text.replace("\r\n", "\n").replace("\r", "\n")


def coerce_cell_text(value: Any) -> str:
    """Convertit une valeur en texte CSV."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
