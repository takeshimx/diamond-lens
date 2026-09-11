"""
HITL フライホイール (trace 期待値 → golden_dataset) のテスト。

BigQuery には一切アクセスしない。検証ロジックと語彙の導出、および
golden_dataset への変換だけを対象とする。
"""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services import golden_promotion_service as promo
from app.services import trace_expectation_service as svc

GOLDEN_PATH = Path(__file__).parent / "golden_dataset.json"


# ── 語彙の導出 ────────────────────────────────────────────────


class TestVocabulary:
    """選択肢は tool schema の enum から導出されること。"""

    def test_query_types_are_flat_not_dotted(self):
        """splits は "batting_splits" であって "batting_splits.risp" ではない。

        LLM が実際に出力するのは query_type + split_type の 2 フィールドで、
        golden_dataset もその形。ドット結合すると評価スクリプトと噛み合わない。
        """
        types = svc.valid_query_types()
        assert "batting_splits" in types
        assert not any("." in t for t in types)

    def test_split_types_only_for_splits_query_types(self):
        splits = svc.valid_split_types()
        assert set(splits) == {"batting_splits", "pitching_splits"}
        assert "risp" in splits["batting_splits"]
        # 投手側に打者用の split が混ざっていないこと
        assert "risp" not in splits["pitching_splits"]
        assert "count_situation" in splits["pitching_splits"]

    def test_metrics_include_main_stats_keyword(self):
        """main_stats は METRIC_MAP に無いが base_engine が展開する特殊キーワード。"""
        metrics = svc.valid_metrics()
        assert "main_stats" in metrics
        assert "batting_average" in metrics

    def test_vocabulary_covers_existing_golden_dataset(self):
        """既存 golden の語彙が全て選択肢に含まれること。

        ここが落ちるということは、UI から入力した期待値が既存ケースと
        別の綴りになるということ。CI ゲートが意味不明な理由で落ちる。
        """
        golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
        query_types = set(svc.valid_query_types())
        metrics = set(svc.valid_metrics())
        all_splits = {v for vs in svc.valid_split_types().values() for v in vs}

        for case in golden["test_cases"]:
            expected = case.get("expected", {})
            if not expected.get("query_type"):
                continue
            assert expected["query_type"] in query_types, case["id"]
            for m in expected.get("metrics_contains", []):
                assert m in metrics, f"{case['id']}: {m}"
            if expected.get("split_type"):
                assert expected["split_type"] in all_splits, case["id"]


# ── 検証 ─────────────────────────────────────────────────────


class TestValidation:
    """UI が選択肢から選ぶ設計でも API は直接叩ける。サーバ側で必ず弾く。"""

    def test_rejects_unknown_query_type(self):
        with pytest.raises(ValueError, match="unknown query_type"):
            svc._validate("TODO", [], None)

    def test_rejects_unknown_metric(self):
        with pytest.raises(ValueError, match="unknown metrics"):
            svc._validate("season_batting", ["TODO"], None)

    def test_rejects_split_type_on_non_splits_query_type(self):
        with pytest.raises(ValueError, match="does not take split_type"):
            svc._validate("season_batting", [], "risp")

    def test_rejects_pitcher_split_on_batter_query_type(self):
        with pytest.raises(ValueError, match="unknown split_type"):
            svc._validate("batting_splits", [], "count_situation")

    def test_accepts_valid_combination(self):
        svc._validate("batting_splits", ["batting_average"], "risp")

    def test_put_expectation_skips_validation_when_no_tool_expected(self):
        """断るのが正解のケースは query_type を持たない。"""
        with patch.object(svc, "_get_client") as mock_client:
            mock_client.return_value.insert_rows_json.return_value = []
            row = svc.put_expectation(
                trace_id="t1",
                user_query="1850年の打率は？",
                query_type="",
                expected_no_tool=True,
            )
        assert row["expected_no_tool"] is True

    def test_put_expectation_raises_on_insert_error(self):
        with patch.object(svc, "_get_client") as mock_client:
            mock_client.return_value.insert_rows_json.return_value = [
                {"index": 0, "errors": [{"reason": "invalid"}]}
            ]
            with pytest.raises(RuntimeError, match="failed to insert"):
                svc.put_expectation(
                    trace_id="t1",
                    user_query="q",
                    query_type="season_batting",
                    metrics=["homerun"],
                )

    def test_put_expectation_serialises_metrics_as_json(self):
        """metrics は既存の tool_calls 列と同じく JSON 文字列で保存する。"""
        with patch.object(svc, "_get_client") as mock_client:
            insert = mock_client.return_value.insert_rows_json
            insert.return_value = []
            svc.put_expectation(
                trace_id="t1",
                user_query="q",
                query_type="season_batting",
                metrics=["homerun", "batting_average"],
            )
        written = insert.call_args[0][1][0]
        assert json.loads(written["metrics"]) == ["homerun", "batting_average"]


# ── golden への変換 ──────────────────────────────────────────


def _expectation(trace_id: str, **overrides):
    """list_expectations が返す 1 件分の形。"""
    base = {
        "trace_id": trace_id,
        "request_id": None,
        "user_query": "q",
        "query_type": "season_batting",
        "split_type": None,
        "metrics": ["homerun"],
        "player_name": None,
        "season": None,
        "order_by": None,
        "expected_no_tool": False,
    }
    base.update(overrides)
    return base


def _load_promote_module():
    """scripts/approve_to_golden.py を import する（tests からは非パッケージ）。"""
    import sys

    scripts = Path(__file__).resolve().parent.parent / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        return importlib.import_module("approve_to_golden")
    finally:
        sys.path.remove(str(scripts))


class TestGoldenConversion:
    def test_omits_unset_fields(self):
        """値の無いキーを入れると None が期待値として採点されてしまう。"""
        case = promo.to_golden_case(
            {
                "trace_id": "t1",
                "user_query": "2025年の本塁打王は？",
                "query_type": "season_batting",
                "split_type": None,
                "metrics": ["homerun"],
                "player_name": None,
                "season": 2025,
                "order_by": "homerun",
                "expected_no_tool": False,
            },
            41,
        )
        assert case["id"] == "GD-AUTO-041"
        assert case["source_trace_id"] == "t1"
        assert "name" not in case["expected"]
        assert "split_type" not in case["expected"]
        assert case["expected"]["order_by"] == "homerun"
        assert case["expected"]["season"] == 2025

    def test_abstain_case_shape(self):
        case = promo.to_golden_case(
            {
                "trace_id": "t2",
                "user_query": "1850年の打率は？",
                "query_type": "",
                "metrics": [],
                "expected_no_tool": True,
            },
            42,
        )
        assert case["expected_no_tool"] is True
        assert case["expected"] == {}

    def test_already_promoted_traces_are_skipped(self, tmp_path, monkeypatch):
        """source_trace_id による重複排除。trace_expectations は追記のみのため、
        「処理済み」の状態は昇格先である golden 側に持たせる。"""
        mod = _load_promote_module()
        golden = {
            "version": "test",
            "test_cases": [
                {"id": "GD-001", "query": "q", "source_trace_id": "t1", "expected": {}}
            ],
        }
        path = tmp_path / "golden.json"
        path.write_text(json.dumps(golden), encoding="utf-8")
        monkeypatch.setattr(mod, "GOLDEN_FILE", str(path))
        monkeypatch.setattr(
            mod,
            "list_expectations",
            lambda days: [
                {
                    "trace_id": "t1",  # 既に昇格済み
                    "user_query": "q",
                    "query_type": "season_batting",
                    "metrics": [],
                    "expected_no_tool": False,
                }
            ],
        )
        assert mod.promote(days=90, apply=False) == 0

    def test_dry_run_does_not_write(self, tmp_path, monkeypatch):
        mod = _load_promote_module()
        # カテゴリ最低件数の規則を満たすため、既存を 2 件置いておく
        golden = {
            "version": "test",
            "test_cases": [
                {"id": "GD-001", "category": "season_batting", "expected": {}},
                {"id": "GD-002", "category": "season_batting", "expected": {}},
            ],
        }
        path = tmp_path / "golden.json"
        path.write_text(json.dumps(golden), encoding="utf-8")
        monkeypatch.setattr(mod, "GOLDEN_FILE", str(path))
        monkeypatch.setattr(
            mod, "list_expectations", lambda days: [_expectation("t9")]
        )
        assert mod.promote(days=90, apply=False) == 1
        assert len(json.loads(path.read_text(encoding="utf-8"))["test_cases"]) == 2


class TestPromotionGuards:
    """golden の構造テストを壊すものは昇格させない。

    ここを通してしまうと、精度ゲート以前に CI が構造エラーで落ちる。
    """

    def _run(self, mod, tmp_path, monkeypatch, existing, pending):
        path = tmp_path / "golden.json"
        path.write_text(
            json.dumps({"version": "test", "test_cases": existing}), encoding="utf-8"
        )
        monkeypatch.setattr(mod, "GOLDEN_FILE", str(path))
        monkeypatch.setattr(mod, "list_expectations", lambda days: pending)
        return mod.promote(days=90, apply=False)

    def test_holds_unimplemented_query_type(self, tmp_path, monkeypatch):
        """query_maps に無い query_type は昇格させない。

        career_pitching は tool schema の enum にはあるが query_maps に実装が無い。
        入れるとプロンプトを幾ら直しても緑にならず、CI が永久に赤くなる。
        """
        mod = _load_promote_module()
        existing = [
            {"id": f"GD-00{i}", "category": "career_pitching", "expected": {}}
            for i in range(1, 4)
        ]
        pending = [_expectation("t1", query_type="career_pitching")]
        assert self._run(mod, tmp_path, monkeypatch, existing, pending) == 0

    def test_holds_category_below_minimum(self, tmp_path, monkeypatch):
        """新カテゴリを 1 件だけ入れると test_category_coverage が落ちる。"""
        mod = _load_promote_module()
        pending = [_expectation("t1", query_type="career_batting")]
        assert self._run(mod, tmp_path, monkeypatch, [], pending) == 0

    def test_promotes_when_batch_completes_category(self, tmp_path, monkeypatch):
        """同カテゴリが規定数まで揃えば、その回で一括昇格する。"""
        mod = _load_promote_module()
        pending = [
            _expectation(f"t{i}", query_type="career_batting") for i in range(3)
        ]
        assert self._run(mod, tmp_path, monkeypatch, [], pending) == 3


# ── list_traces の 👎 フィルタ ────────────────────────────────


class TestBadRatingFilter:
    def test_query_joins_feedback_by_request_id(self):
        """👎 の行は trace_id が NULL なので request_id で結ぶ必要がある。

        実データで trace_id / node がいずれも NULL であることを確認済み
        (llm_logger_service._update_bigquery_feedback が別行として INSERT する)。
        """
        from app.services import trace_query_service as tqs

        with patch.object(tqs, "_get_client") as mock_client:
            mock_client.return_value.query.return_value.result.return_value = []
            tqs.list_traces(only_bad_rating=True)

        sql = mock_client.return_value.query.call_args[0][0]
        assert "LEFT JOIN feedback" in sql
        assert "USING (request_id)" in sql
        assert "@only_bad_rating = FALSE OR f.user_rating = 'bad'" in sql

    def test_bad_rating_param_is_passed(self):
        from app.services import trace_query_service as tqs

        with patch.object(tqs, "_get_client") as mock_client:
            mock_client.return_value.query.return_value.result.return_value = []
            tqs.list_traces(only_bad_rating=True)

        job_config = mock_client.return_value.query.call_args[1]["job_config"]
        params = {p.name: p.value for p in job_config.query_parameters}
        assert params["only_bad_rating"] is True

    def test_get_trace_reads_feedback_separately(self):
        """trace_id 検索だけでは 👎 を拾えないため、request_id で引き直すこと。"""
        from app.services import trace_query_service as tqs

        row = MagicMock()
        row.__getitem__.side_effect = lambda k: {
            "user_rating": "bad",
            "feedback_category": "wrong_player",
            "feedback_reason": "別人が返ってきた",
        }[k]

        with patch.object(tqs, "_get_client") as mock_client:
            mock_client.return_value.query.return_value.result.return_value = [row]
            result = tqs._fetch_feedback("req-1")

        assert result["user_rating"] == "bad"
        assert result["feedback_category"] == "wrong_player"

    def test_fetch_feedback_returns_none_when_absent(self):
        from app.services import trace_query_service as tqs

        with patch.object(tqs, "_get_client") as mock_client:
            mock_client.return_value.query.return_value.result.return_value = []
            assert tqs._fetch_feedback("req-1") is None


# ── PR 自動作成 ──────────────────────────────────────────────


class TestGoldenPR:
    """GitHub API は叩かない。設定と組み立てだけを検証する。"""

    @staticmethod
    def _stub_settings(monkeypatch, token=None, repo=None):
        """.env は pydantic-settings が Settings に読み込むため、環境変数を
        消すだけでは実際の認証情報が残る。Settings ごと差し替える。"""
        from app.services import golden_pr_service as pr

        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_REPO", raising=False)
        monkeypatch.setattr(
            pr,
            "get_settings",
            lambda: SimpleNamespace(
                github_token=token, github_repo=repo, github_base_branch="main"
            ),
        )
        return pr

    def test_raises_clear_error_when_unconfigured(self, monkeypatch):
        pr = self._stub_settings(monkeypatch)
        assert pr.is_configured() is False
        with pytest.raises(pr.GoldenPRError, match="GITHUB_TOKEN"):
            pr.create_golden_pr()

    def test_is_configured_requires_both(self, monkeypatch):
        pr = self._stub_settings(monkeypatch, token="x")
        assert pr.is_configured() is False
        pr = self._stub_settings(monkeypatch, token="x", repo="owner/repo")
        assert pr.is_configured() is True

    def test_pr_body_lists_added_and_held(self):
        from app.services import golden_pr_service as pr

        body = pr._pr_body(
            [{
                "id": "GD-AUTO-041",
                "query": "カーショウの通算奪三振は？",
                "source_trace_id": "t1",
                "expected": {"query_type": "career_pitching"},
            }],
            {"t2": "未実装のため保留"},
        )
        assert "GD-AUTO-041" in body
        assert "t1" in body
        assert "未実装のため保留" in body
        # 追加ケースが落ちても PR の不備ではない、という但し書きを必ず残す
        assert "accuracy gate" in body

    def test_promotion_is_shared_with_cli(self):
        """UI 経由と CLI 経由で判定がずれないこと。"""
        import inspect

        from app.services import golden_pr_service as pr

        cli = _load_promote_module()
        # conftest が backend/ と その親の両方を sys.path に入れているため、
        # `app.services...` と `backend.app.services...` は別オブジェクトになる。
        # 同一性ではなく「同じソースを使っているか」で判定する。
        source = inspect.getsourcefile(promo.build_promotion)
        assert inspect.getsourcefile(cli.build_promotion) == source
        assert inspect.getsourcefile(pr.build_promotion) == source
