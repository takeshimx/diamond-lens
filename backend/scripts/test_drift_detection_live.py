#!/usr/bin/env python3
"""
Live Data Drift Detection Test (with BigQuery Logging)
実データを使ってドリフト検知 + BigQuery ログ記録の動作確認を行うスクリプト。

Usage:
    cd diamond-lens
    set PYTHONPATH=.
    python backend/scripts/test_drift_detection_live.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.app.services.data_drift_service import DataDriftService
from backend.app.services.ml_monitoring_logger import get_ml_monitoring_logger


def print_separator(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_feature_result(f):
    """特徴量ごとの結果を見やすく表示"""
    icon = "✅" if f.severity == "none" else (
        "🟡" if f.severity == "warning" else "🔴"
    )
    print(f"  {icon} {f.feature_name}")
    print(f"     KS statistic : {f.ks_statistic:.4f}")
    print(f"     KS p-value   : {f.ks_p_value:.6f}")
    print(f"     PSI           : {f.psi_value:.4f}")
    print(f"     Mean baseline : {f.mean_baseline:.4f}")
    print(f"     Mean target   : {f.mean_target:.4f}")
    print(f"     Mean shift    : {f.mean_shift_pct:+.2f}%")
    print(f"     Severity      : {f.severity}")
    print()


def main():
    print("\n🔬 ML Data Drift Detection — Live Test (with BigQuery Logging)")
    print("=" * 70)

    service = DataDriftService()
    logger = get_ml_monitoring_logger()

    test_cases = [
        {
            "model_type": "batter_segmentation",
            "baseline_season": 2024,
            "target_season": 2025,
        },
        {
            "model_type": "pitcher_segmentation",
            "baseline_season": 2024,
            "target_season": 2025,
        },
    ]

    reports = []

    # ============================================================
    # Phase 1: ドリフト検知 + BigQuery ログ記録
    # ============================================================
    for case in test_cases:
        print_separator(
            f"{case['model_type']} ({case['baseline_season']} → {case['target_season']})"
        )

        try:
            report = service.detect_drift(
                baseline_season=case["baseline_season"],
                target_season=case["target_season"],
                model_type=case["model_type"],
            )
            reports.append(report)

            # 各特徴量の結果を表示
            print(f"\n  Features ({len(report.features)}):")
            print(f"  {'-'*50}")
            for f in report.features:
                print_feature_result(f)

            print(f"  📊 Overall drift detected: {report.overall_drift_detected}")
            print(f"  📝 Summary: {report.summary}")
            print(f"  🔑 Report ID: {report.report_id}")

            # BigQuery にログ記録
            logger.log_drift_report(report)
            print(f"  📤 Logged to BigQuery (async)")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()

    # ============================================================
    # Phase 2: 非同期書き込みを待ってから読み戻し確認
    # ============================================================
    print_separator("BigQuery Log Verification")
    print("  ⏳ Waiting 10s for async writes to complete...")
    time.sleep(10)

    for model_type in ["batter_segmentation", "pitcher_segmentation"]:
        print(f"\n  📖 Querying drift history: {model_type}")
        history = logger.get_drift_history(model_type=model_type, limit=10)

        if history:
            print(f"     ✅ Found {len(history)} records in BigQuery")
            latest = history[0]
            print(f"     Latest: report_id={latest.get('report_id', 'N/A')[:8]}..., "
                  f"feature={latest.get('feature_name', 'N/A')}, "
                  f"severity={latest.get('severity', 'N/A')}, "
                  f"psi={latest.get('psi_value', 'N/A')}")
        else:
            print(f"     ⚠️  No records found (table may not exist yet)")

    # サマリ取得テスト
    print(f"\n  📊 Querying latest summary: batter_segmentation")
    summary = logger.get_latest_summary("batter_segmentation")
    if summary:
        print(f"     ✅ Summary retrieved: "
              f"drifted={summary.get('drifted_feature_count', 'N/A')}/"
              f"{summary.get('total_feature_count', 'N/A')} features, "
              f"max_psi={summary.get('max_psi', 'N/A')}")
    else:
        print(f"     ⚠️  No summary found")

    print(f"\n{'='*70}")
    print("✅ Live test complete (drift detection + BigQuery logging)!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
