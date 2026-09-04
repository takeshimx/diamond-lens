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
    CATEGORY_DISTANCE_THRESHOLDS,
    DEFAULT_DISTANCE_THRESHOLD,
    EXCLUDED_CATEGORIES,
    VALID_CATEGORIES,
    GlossaryRAGService,
    resolve_distance_threshold,
)


def _make_service(mock_client: MagicMock) -> GlossaryRAGService:
    """BQ クライアントをモックに差し替えたサービスを作る。

    _client を直接セットすることで client プロパティの遅延初期化を回避し、
    bigquery.Client() が呼ばれないようにする。
    """
    svc = GlossaryRAGService()
    svc._client = mock_client
    return svc


def _query_params(job_config) -> dict:
    """QueryJobConfig からパラメータ名 -> 値の辞書を作る。

    ScalarQueryParameter は .value、ArrayQueryParameter は .values を持つ。
    両方が混在するため、素直に p.value を読むと AttributeError になる。
    """
    return {
        p.name: getattr(p, "value", None) if hasattr(p, "value") else p.values
        for p in job_config.query_parameters
    }


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
    params = _query_params(job_config)
    assert params["category"] is None


def test_valid_category_is_passed_through():
    """正しい category はそのままクエリパラメータに渡る。"""
    mock_client = MagicMock()
    mock_client.query.return_value.result.return_value = []
    svc = _make_service(mock_client)

    svc.search("xwOBAとは何ですか", category="batting")

    job_config = mock_client.query.call_args.kwargs["job_config"]
    params = _query_params(job_config)
    assert params["category"] == "batting"


def test_excluded_category_is_not_offered_as_valid():
    """除外中のカテゴリは VALID_CATEGORIES に現れない。

    LLM に選ばせる選択肢（ツール定義の enum）はここから導出しているため、
    片方だけ更新して選択肢と実装が食い違う事故を防ぐ。
    """
    for c in EXCLUDED_CATEGORIES:
        assert c not in VALID_CATEGORIES


# ---------------------------------------------------------------- threshold


def test_threshold_defaults_when_category_is_none():
    """カテゴリ未指定なら用語集用の既定値を使う。"""
    assert resolve_distance_threshold(None) == DEFAULT_DISTANCE_THRESHOLD
    assert resolve_distance_threshold("") == DEFAULT_DISTANCE_THRESHOLD


def test_threshold_is_per_category():
    """カテゴリ別に閾値を上書きできる。

    rules は日本語の質問から英語の条文を引くクロスリンガル検索になり、
    距離分布が用語集（日本語同士）より遠い側へ寄るため専用値が要る。
    """
    assert resolve_distance_threshold("rules") == CATEGORY_DISTANCE_THRESHOLDS["rules"]
    assert resolve_distance_threshold("rules") > DEFAULT_DISTANCE_THRESHOLD
    # 上書きの無いカテゴリは既定値のまま
    assert resolve_distance_threshold("batting") == DEFAULT_DISTANCE_THRESHOLD


def test_search_applies_category_specific_threshold():
    """search() は category に応じた閾値で足切りする。

    用語集用の 0.275 なら捨てられる距離 0.30 の結果が、
    rules 用の閾値なら残ることを確認する。
    """
    mock_client = MagicMock()
    mock_client.query.return_value.result.return_value = [_row("BALK", 0.30)]

    # batting（既定値 0.275）では捨てられる
    svc = _make_service(mock_client)
    assert svc.search("ボークとは", category="batting") == []

    # 明示指定した閾値は引数が優先される（カテゴリ別の既定値を上書きできる）
    svc = _make_service(mock_client)
    hits = svc.search("ボークとは", category="batting", distance_threshold=0.35)
    assert [h["section"] for h in hits] == ["BALK"]
