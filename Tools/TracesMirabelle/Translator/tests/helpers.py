from typing import Any


def make_run_program(
    *,
    user: str = "user1",
    code_state: str = "print('hello')\n",
    success: bool = True,
    stdout: str = "hello\n",
    stderr: str = "",
    timestamp: str = "2026-04-27T12:00:00Z",
    session_id: str = "session-1",
) -> dict[str, Any]:
    return {
        "verb": {"id": "https://www.cristal.univ-lille.fr/verbs/Run.Program"},
        "actor": {"openid": f"https://www.cristal.univ-lille.fr/users/{user}/"},
        "timestamp": timestamp,
        "object": {
            "extension": {
                "https://www.cristal.univ-lille.fr/objects/Program/CodeState": code_state,
            }
        },
        "context": {
            "extension": {
                "https://www.cristal.univ-lille.fr/objects/Session/ID": session_id,
            }
        },
        "result": {
            "success": success,
            "extension": {
                "https://www.cristal.univ-lille.fr/objects/Command/stdout": stdout,
                "https://www.cristal.univ-lille.fr/objects/Command/stderr": stderr,
            },
        },
    }


def make_run_debugger(
    *,
    user: str = "user1",
    code_state: str = "x = 2\ny = 3\n",
    lineno: int = 2,
    success: bool = True,
    stdout: str = "debug\n",
    stderr: str = "",
    timestamp: str = "2026-04-27T12:00:01Z",
) -> dict[str, Any]:
    return {
        "verb": {"id": "https://www.cristal.univ-lille.fr/verbs/Run.Debugger"},
        "actor": {"openid": f"https://www.cristal.univ-lille.fr/users/{user}/"},
        "timestamp": timestamp,
        "object": {
            "extension": {
                "https://www.cristal.univ-lille.fr/objects/Program/CodeState": code_state,
                "https://www.cristal.univ-lille.fr/objects/Program/Lineno": lineno,
            }
        },
        "result": {
            "success": success,
            "extension": {
                "https://www.cristal.univ-lille.fr/objects/Command/stdout": stdout,
                "https://www.cristal.univ-lille.fr/objects/Command/stderr": stderr,
            },
        },
    }


def make_run_test(
    *,
    user: str = "user1",
    code_state: str = "print('tests')\n",
    tests: list[dict[str, Any]] | None = None,
    status: bool | None = None,
    error: str | None = None,
    timestamp: str = "2026-04-27T12:00:02Z",
) -> dict[str, Any]:
    statement = {
        "verb": {"id": "https://www.cristal.univ-lille.fr/verbs/Run.test"},
        "actor": {"openid": f"https://www.cristal.univ-lille.fr/users/{user}/"},
        "timestamp": timestamp,
        "object": {
            "extension": {
                "https://www.cristal.univ-lille.fr/objects/Program/CodeState": code_state,
                "https://www.cristal.univ-lille.fr/objects/Tests/Tests": tests
                if tests is not None
                else [
                    {"lineno": 1, "verdict": "PassedVerdict"},
                ],
            }
        },
        "result": {},
    }

    if status is not None:
        statement["object"]["extension"]["https://www.cristal.univ-lille.fr/objects/Tests/Status"] = status
    if error is not None:
        statement["object"]["extension"]["https://www.cristal.univ-lille.fr/objects/Tests/Error"] = error

    return statement


def make_file_save(*, user: str = "user1", timestamp: str = "2026-04-27T12:00:03Z") -> dict[str, Any]:
    return {
        "verb": {"id": "https://www.cristal.univ-lille.fr/verbs/File.Save"},
        "actor": {"openid": f"https://www.cristal.univ-lille.fr/users/{user}/"},
        "timestamp": timestamp,
    }


def make_multi_user_statements() -> list[dict[str, Any]]:
    return [
        make_run_program(user="alice", code_state="print('shared')\r\n", success=True, stdout="ok\n"),
        make_run_debugger(user="bob", code_state="print('shared')\n", lineno=3, success=False, stdout="step\n", stderr="Traceback: boom"),
        make_run_test(user="alice", code_state="print('tests')\n"),
        make_file_save(user="bob"),
    ]
