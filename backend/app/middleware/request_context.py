from contextvars import ContextVar

_request_id_var: ContextVar[str] = ContextVar("request_id", default="")
_user_id_var: ContextVar[str] = ContextVar("user_id", default="")
# Snowflake-style 横断的 trace id。Phase 2 では request_id と並走させ、
# Phase 3 以降で BQ ログ・SSE event payload にも流す。
_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
# HTTP リクエストのエンドポイントパス。LLM ロガーが自動取得用に使う。
_endpoint_var: ContextVar[str] = ContextVar("endpoint", default="")
# session_id (フロントからの会話セッション識別子)。LLM ロガーが自動取得用に使う。
_session_id_var: ContextVar[str] = ContextVar("session_id", default="")
# BigQuery クエリの累計実行時間 (ms)。1 リクエスト内で複数 BQ クエリが走った場合は合算。
# analytics service が add_bq_latency_ms() で加算し、エンドポイントが最後に読む。
_bq_latency_ms_var: ContextVar[float] = ContextVar("bq_latency_ms", default=0.0)


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


def get_endpoint() -> str:
    return _endpoint_var.get()


def set_endpoint(endpoint: str) -> None:
    _endpoint_var.set(endpoint)


def get_session_id() -> str:
    return _session_id_var.get()


def set_session_id(session_id: str) -> None:
    _session_id_var.set(session_id)


def get_bq_latency_ms() -> float:
    return _bq_latency_ms_var.get()


def add_bq_latency_ms(ms: float) -> None:
    _bq_latency_ms_var.set(_bq_latency_ms_var.get() + ms)


def reset_bq_latency_ms() -> None:
    _bq_latency_ms_var.set(0.0)