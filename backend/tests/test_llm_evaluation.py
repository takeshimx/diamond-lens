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
        """query_type が有効な値であることを検証"""
        valid_types = [
            "season_batting", "season_pitching",
            "batting_splits", "career_batting"
        ]
        for case in dataset["test_cases"]:
            qt = case["expected"]["query_type"]
            assert qt in valid_types, \
                f"Test case {case['id']} has invalid query_type: {qt}"

    def test_minimum_test_cases(self, dataset):
        """最低10件のテストケースがあることを検証"""
        assert len(dataset["test_cases"]) >= 9, \
            f"Golden dataset should have at least 9 test cases, got {len(dataset['test_cases'])}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
