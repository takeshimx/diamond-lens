from contextvars import ContextVar

_request_id_var: ContextVar[str] = ContextVar("request_id", default="")
_user_id_var: ContextVar[str] = ContextVar("user_id", default="")
# Snowflake-style 横断的 trace id。Phase 2 では request_id と並走させ、
# Phase 3 以降で BQ ログ・SSE event payload にも流す。
_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def get_request_id() -> str:
    return _request_id_var.get()


def set_request_id(request_id: str) -> None:
    _request_id_var.set(request_id)

def get_user_id() -> str:
    return _user_id_var.get()


def set_user_id(user_id: str) -> None:
    _user_id_var.set(user_id)


def get_trace_id() -> str:
    return _trace_id_var.get()


def set_trace_id(trace_id: str) -> None:
    _trace_id_var.set(trace_id)