# backend/tests/test_shadow_logger.py
"""
ADR-019 Compliance: shadow 評価が本番フローに影響しないことの検証。

シャドー評価の鉄則は「challenger 側が何をしくじっても、ユーザーへの
応答にも本番のレイテンシにも影響しない」こと。その保証を呼び出し側の
try/except に委ねると、新しい呼び出し箇所が 1 つ囲み忘れた時点で破れる。
したがって log() 自身が決して例外を送出しないことを固定する。
"""

from unittest.mock import Mock, patch

from backend.app.services.shadow_logger_service import (
    ShadowComparisonEntry,
    ShadowLoggerService,
)

_MODULE = "backend.app.services.shadow_logger_service"


def _service_with_fake_client() -> ShadowLoggerService:
    """BigQuery へ実接続しない ShadowLoggerService を作る。"""
    with patch(f"{_MODULE}.bigquery.Client"):
        service = ShadowLoggerService()
    service.client = Mock()
    return service


def test_log_does_not_raise_when_entry_serialization_fails():
    """entry.to_dict() が壊れても log() は例外を出さない。

    to_dict() は書き込みスレッドではなく呼び出し元スレッドで実行される。
    ここが本番フローへ例外が漏れうる唯一の経路である。
    """
    service = _service_with_fake_client()
    entry = ShadowComparisonEntry()
    entry.to_dict = Mock(side_effect=RuntimeError("serialization boom"))

    service.log(entry)  # 例外が送出されないこと自体が検証内容


def test_log_does_not_raise_when_thread_cannot_start():
    """スレッドを起動できなくても log() は例外を出さない。"""
    service = _service_with_fake_client()

    with patch(f"{_MODULE}.threading.Thread") as thread_cls:
        thread_cls.return_value.start.side_effect = RuntimeError(
            "can't start new thread"
        )
        service.log(ShadowComparisonEntry())


def test_write_to_bigquery_swallows_insert_errors():
    """BigQuery が落ちても書き込みスレッド側で握り潰す。"""
    service = _service_with_fake_client()
    service.client.insert_rows_json.side_effect = RuntimeError("BQ unavailable")

    service._write_to_bigquery({"comparison_id": "test"})


def test_log_writes_on_a_daemon_thread():
    """書き込みは daemon スレッドへ逃がし、呼び出し元をブロックしない。

    実時間のアサートは CI で不安定になるため、Thread へ渡した引数を検証する。
    """
    service = _service_with_fake_client()

    with patch(f"{_MODULE}.threading.Thread") as thread_cls:
        service.log(ShadowComparisonEntry())

    assert thread_cls.call_args.kwargs["daemon"] is True
    thread_cls.return_value.start.assert_called_once()


def test_log_skips_when_client_is_unavailable():
    """クライアント初期化に失敗している場合は、何もせず静かに返る。"""
    service = _service_with_fake_client()
    service.client = None

    with patch(f"{_MODULE}.threading.Thread") as thread_cls:
        service.log(ShadowComparisonEntry())

    thread_cls.assert_not_called()
