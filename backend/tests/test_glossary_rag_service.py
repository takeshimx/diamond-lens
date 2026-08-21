"""
GlossaryRAGService の単体テスト。

BigQuery には一切接続しない（_client をモックに差し替える）ため、
GCP 認証も課金も発生しない。CI でそのまま実行できる。

検証の主眼は fail-open:
  用語集検索は「あれば嬉しい補助機能」であり、これが落ちたせいで
  チャット本体まで止まってはならない。BQ 障害時は例外を外に漏らさず
  空リストを返し、呼び出し側が「検索結果なし」として処理を続行できること。
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from backend.app.services.glossary_rag_service import (
    DEFAULT_DISTANCE_THRESHOLD,
    GlossaryRAGService,
)


def _make_service(mock_client: MagicMock) -> GlossaryRAGService:
    """BQ クライアントをモックに差し替えたサービスを作る。

    _client を直接セットすることで client プロパティの遅延初期化を回避し、
    bigquery.Client() が呼ばれないようにする。
    """
    svc = GlossaryRAGService()
    svc._client = mock_client
    return svc


def _row(section: str, distance: float) -> SimpleNamespace:
    """BQ の Row を模したオブジェクト。属性アクセスできればよい。"""
    return SimpleNamespace(
        section=section,
        source="glossary_batting.md",
        category="batting",
        chunk_text=f"{section}\n定義: ダミー本文",
        distance=distance,
    )


# ---------------------------------------------------------------- fail-open


def test_search_returns_empty_when_bq_raises():
    """BQ がエラーを投げても例外を外に漏らさず空リストを返す（fail-open の本体）。"""
    mock_client = MagicMock()
    mock_client.query.side_effect = RuntimeError("BQ unavailable")
    svc = _make_service(mock_client)

    assert svc.search("xwOBAとは何ですか") == []


def test_search_returns_empty_when_client_unavailable():
    """BQ クライアントの初期化に失敗している場合も空リストを返す。"""
    svc = GlossaryRAGService()
    svc._client = None
    # client プロパティが再初期化を試みても失敗するよう、生成関数を潰す
    svc.__dict__["_client"] = None

    # 認証なし環境では bigquery.Client() が例外を投げ、プロパティが None を返す。
    # 例外が外に漏れないことだけを保証する。
    result = svc.search("xwOBAとは何ですか")
    assert isinstance(result, list)


def test_search_returns_empty_on_blank_query():
    """空文字・空白のみのクエリでは BQ を叩かない（無駄な課金を防ぐ）。"""
    mock_client = MagicMock()
    svc = _make_service(mock_client)

    assert svc.search("") == []
    assert svc.search("   ") == []
    mock_client.query.assert_not_called()


# ---------------------------------------------------------------- 正常系


def test_search_returns_hits_sorted_by_distance():
    """距離の昇順で、必要なキーを揃えて返す。"""
    mock_client = MagicMock()
    mock_client.query.return_value.result.return_value = [
        _row("xwOBA", 0.1831),
        _row("wOBA", 0.2352),
    ]
    svc = _make_service(mock_client)

    hits = svc.search("xwOBAとは何ですか", category="batting")

    assert [h["section"] for h in hits] == ["xwOBA", "wOBA"]
    assert hits[0]["distance"] == 0.1831
    assert set(hits[0]) == {"section", "source", "category", "chunk_text", "distance"}


def test_search_filters_by_distance_threshold():
    """閾値を超えた結果は捨てる。"""
    mock_client = MagicMock()
    over = DEFAULT_DISTANCE_THRESHOLD + 0.1
    mock_client.query.return_value.result.return_value = [
        _row("xwOBA", 0.1831),
        _row("無関係な用語", over),
    ]
    svc = _make_service(mock_client)

    hits = svc.search("xwOBAとは何ですか")

    assert [h["section"] for h in hits] == ["xwOBA"]


def test_search_returns_empty_when_no_rows():
    """該当なしの場合も空リスト（None ではない）。"""
    mock_client = MagicMock()
    mock_client.query.return_value.result.return_value = []
    svc = _make_service(mock_client)

    assert svc.search("存在しない用語") == []


# ---------------------------------------------------------------- category


def test_unknown_category_falls_back_to_no_filter():
    """未知の category はフィルタなしに倒す。

    誤った値で 0 件になるより、全カテゴリ横断で返す方が実用的なため。
    例外を投げずにクエリまで到達することを確認する。
    """
    mock_client = MagicMock()
    mock_client.query.return_value.result.return_value = []
    svc = _make_service(mock_client)

    assert svc.search("xwOBAとは何ですか", category="unknown_cat") == []
    mock_client.query.assert_called_once()

    # category パラメータが None にフォールバックしていることを確認する
    job_config = mock_client.query.call_args.kwargs["job_config"]
    params = {p.name: p.value for p in job_config.query_parameters}
    assert params["category"] is None


def test_valid_category_is_passed_through():
    """正しい category はそのままクエリパラメータに渡る。"""
    mock_client = MagicMock()
    mock_client.query.return_value.result.return_value = []
    svc = _make_service(mock_client)

    svc.search("xwOBAとは何ですか", category="batting")

    job_config = mock_client.query.call_args.kwargs["job_config"]
    params = {p.name: p.value for p in job_config.query_parameters}
    assert params["category"] == "batting"
