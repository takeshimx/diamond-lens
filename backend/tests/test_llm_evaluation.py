"""
ゴールデンデータセットの構造バリデーションテスト

LLMを呼び出さずに、golden_dataset.json の構造が正しいことを検証します。
"""

import pytest
import json
from pathlib import Path

GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"


class TestGoldenDatasetStructure:
    """ゴールデンデータセットの構造を検証"""

    @pytest.fixture
    def dataset(self):
        with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_dataset_has_test_cases(self, dataset):
        """データセットにテストケースが存在することを検証"""
        assert "test_cases" in dataset
        assert len(dataset["test_cases"]) > 0

    def test_all_cases_have_required_fields(self, dataset):
        """全テストケースが必須フィールドを持つことを検証"""
        required_fields = ["id", "category", "query", "expected"]
        for case in dataset["test_cases"]:
            for field in required_fields:
                assert field in case, f"Test case {case.get('id', 'unknown')} missing field: {field}"

    def test_all_cases_have_unique_ids(self, dataset):
        """テストケースIDが一意であることを検証"""
        ids = [case["id"] for case in dataset["test_cases"]]
        assert len(ids) == len(set(ids)), "Duplicate test case IDs found"

    def test_expected_has_query_type(self, dataset):
        """全テストケースの expected に query_type が含まれることを検証"""
        for case in dataset["test_cases"]:
            assert "query_type" in case["expected"], \
                f"Test case {case['id']} missing expected.query_type"

    def test_valid_query_types(self, dataset):
        """query_type が有効な値であることを検証。

        有効値はハードコードせず QUERY_TYPE_CONFIG から動的に取得する。
        列挙を二重管理すると、query_maps 側に型を追加した際にここが取り残される。
        """
        from backend.app.config.query_maps import QUERY_TYPE_CONFIG
        valid_types = set(QUERY_TYPE_CONFIG.keys())
        for case in dataset["test_cases"]:
            qt = case["expected"]["query_type"]
            assert qt in valid_types, \
                f"Test case {case['id']} has invalid query_type: {qt}"

    def test_valid_split_types(self, dataset):
        """split_type が該当 query_type で定義済みの値であることを検証"""
        from backend.app.config.query_maps import QUERY_TYPE_CONFIG
        for case in dataset["test_cases"]:
            split_type = case["expected"].get("split_type")
            if split_type is None:
                continue
            qt = case["expected"]["query_type"]
            # splits 系の query_type は、直下のキーがそのまま split_type になる
            # (例: QUERY_TYPE_CONFIG["batting_splits"]["risp"])
            allowed = QUERY_TYPE_CONFIG[qt]
            assert split_type in allowed, \
                f"Test case {case['id']} has invalid split_type '{split_type}' for {qt}"

    def test_minimum_test_cases(self, dataset):
        """最低 40 件のテストケースがあることを検証。

        閾値 80% の CI ゲートに対し、14 件では 1 件 = 7.1% となり
        1 件の揺れで PASS/FAIL が反転する。40 件で 1 件 = 2.5% に抑える。
        """
        assert len(dataset["test_cases"]) >= 40, \
            f"Golden dataset should have at least 40 test cases, got {len(dataset['test_cases'])}"

    def test_category_coverage(self, dataset):
        """各カテゴリが最低 3 件あることを検証。

        全体件数を満たしていても特定カテゴリが 0〜1 件だと、
        そのカテゴリの劣化を検知できないため。
        """
        from collections import Counter
        counts = Counter(case["category"] for case in dataset["test_cases"])
        for category, n in counts.items():
            assert n >= 3, f"Category '{category}' has only {n} case(s); expected >= 3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
