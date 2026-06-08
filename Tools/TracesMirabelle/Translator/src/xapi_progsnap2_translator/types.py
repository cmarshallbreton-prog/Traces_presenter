from typing import Any, Callable

SUCCESS = "Success"
ERROR = "Error"
TOOL_INSTANCES_DEFAULT = "Thonny"

MAIN_TABLE_FIELDS = [
    "EventID",
    "EventType",
    "SubjectID",
    "ToolInstances",
    "CodeStateID",
    "ServerTimestamp",
    "SessionID",
    "ExecutionResult",
    "ProgramInput",
    "ProgramOutput",
    "ProgramErrorOutput",
    "X-RunTestData",
    "Lineno",
]

LINK_TABLE_FIELDS = [
    "SubjectID",
    "X-Identifier",
    "X-TeamID",
]

CODE_STATES_FIELDS = [
    "CodeStateID",
    "Code",
]

DATASET_METADATA_FIELDS = [
    "Property",
    "Value",
]

ALLOWED_EVENT_TYPES = {
    "Run.Program",
    "Run.Test",
    "Debug.Program",
    "Debug.Test",
    "Session.Start",
    "Session.End",
    "File.Open",
    "X-File.Save",
    "X-Run.Command",
    "X-Docstring.Generate",
}

PROGSNAP_EVENT_TYPE_MAP = {
    "Run.test": "Run.Test",
    "Run.Debugger": "Debug.Program",
    "File.Save": "X-File.Save",
    "Run.Command": "X-Run.Command",
    "Docstring.Generate": "X-Docstring.Generate",
}

MainRow = dict[str, str]
LinkRow = dict[str, str]
CodeStateRow = dict[str, str]
DatasetMetadataRow = dict[str, str]
Statement = dict[str, Any]
MainTableHandler = Callable[[Statement, str, str], MainRow]
