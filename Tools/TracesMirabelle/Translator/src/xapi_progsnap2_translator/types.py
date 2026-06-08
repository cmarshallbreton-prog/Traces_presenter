from typing import Any, Callable

SUCCESS = "Success"
ERROR = "Error"

MAIN_TABLE_FIELDS = [
    "SubjectID",
    "EventID",
    "ToolInstances",
    "ServerTimestamp",
    "SessionID",
    "CodeStateID",
    "Order",
    "EventType",
    "RunProgram.Result",
    "RunProgramErrorMessageType",
    "RunProgramOutputData",
    "RunTestData",
    "Lineno",
]

LINK_TABLE_FIELDS = [
    "SubjectID",
    "Identifier",
]

CODE_STATES_FIELDS = [
    "CodeStateID",
    "CodeState",
]

ALLOWED_EVENT_TYPES = {
    "Run.Program",
    "Run.test",
    "Run.Debugger",
}

MainRow = dict[str, str]
LinkRow = dict[str, str]
CodeStateRow = dict[str, str]
Statement = dict[str, Any]
MainTableHandler = Callable[[Statement, int, str], MainRow]
