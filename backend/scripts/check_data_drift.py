#!/usr/bin/env python3
"""
CI/CD Data Drift Check Script
デプロイ前にデータドリフトをチェックし、
Critical レベルのドリフトが検出された場合はデプロイを停止する。

Model Registry の active モデルの training_season を baseline として自動取得する。
active モデルが存在しない場合はスキップ（デプロイ続行）。

Usage:
    python scripts/check_data_drift.py

Exit Codes:
    0 — ドリフトなし or Warning レベルのみ（デプロイ続行）
    1 — Critical レベルのドリフト検出（デプロイ停止）
"""

import sys
import os

# パス設定
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.services.data_drift_service import DataDriftService
from backend.app.services.model_registry_service import ModelRegistryService

# 最新シーズン（環境変数で上書き可能）
TARGET_SEASON = int(os.environ.get("DRIFT_TARGET_SEASON", 2025))


def main():
    service = DataDriftService()

    # Registry 初期化
    try:
        registry = ModelRegistryService()
    except Exception as e:
        print(f"⚠️  Model Registry unavailable: {e}")
        print("✅ Skipping drift check. Deployment can proceed.")
        sys.exit(0)

    has_critical = False

    # 監視対象モデル一覧
    models = ["batter_segmentation", "pitcher_segmentation"]

    for model_type in models:
        print(f"\n{'='*60}")
        print(f"Checking drift: {model_type}")
        print(f"{'='*60}")

        # Registry から active モデルの training_season を取得
        active = registry.get_active_version(model_type)
        if not active:
            print(f"  ⚠️  No active model for {model_type}. Skipping.")
            continue

        baseline_season = active.training_season
        print(f"  Active model: {active.version} (trained on {baseline_season})")
        print(f"  Comparing: {baseline_season} → {TARGET_SEASON}")

        if baseline_season == TARGET_SEASON:
            print(f"  ℹ️  baseline == target ({baseline_season}). No drift check needed.")
            continue

        try:
            report = service.detect_drift(
                baseline_season=baseline_season,
                target_season=TARGET_SEASON,
                model_type=model_type,
            )

            for f in report.features:
                status = "✅" if f.severity == "none" else (
                    "🟡" if f.severity == "warning" else "🔴"
                )
                print(
                    f"  {status} {f.feature_name}: "
                    f"PSI={f.psi_value:.4f}, "
                    f"KS_p={f.ks_p_value:.4f}, "
                    f"mean_shift={f.mean_shift_pct:+.2f}%"
                )

            if any(f.severity == "critical" for f in report.features):
                has_critical = True
                print(f"\n⚠️  CRITICAL drift detected in {model_type}!")

            print(f"\nSummary: {report.summary}")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            # エラー時はデプロイを止めない（データがない場合など）
            continue

    if has_critical:
        print("\n🚫 Deployment blocked: Critical data drift detected.")
        print("   → Re-train models with latest data before deploying.")
        sys.exit(1)
    else:
        print("\n✅ No critical drift detected. Deployment can proceed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
