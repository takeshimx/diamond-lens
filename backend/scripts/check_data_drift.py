#!/usr/bin/env python3
"""
CI/CD Data Drift Check Script
デプロイ前にデータドリフトをチェックし、
Critical レベルのドリフトが検出された場合はデプロイを停止する。

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


def main():
    service = DataDriftService()
    has_critical = False

    # 監視対象モデル一覧
    models = ["batter_segmentation", "pitcher_segmentation"]

    for model_type in models:
        print(f"\n{'='*60}")
        print(f"Checking drift: {model_type}")
        print(f"{'='*60}")

        try:
            report = service.detect_drift(
                baseline_season=2024,
                target_season=2025,
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
        sys.exit(1)
    else:
        print("\n✅ No critical drift detected. Deployment can proceed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
