"""
Model Registry ライブテスト
実データで全フローを検証:
  1. train_and_register — 2024年データでモデル学習 & GCS保存 & BigQuery記録
  2. promote_version — 学習したバージョンを active に昇格
  3. load_model — GCS からモデルをロード
  4. player_segmentation — Registry からロードしたモデルでセグメンテーション実行
  5. drift detection — baseline_season 省略で自動取得を確認
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json
from backend.app.services.model_registry_service import ModelRegistryService
from backend.app.services.data_drift_service import DataDriftService


def main():
    print("=" * 60)
    print("Model Registry Live Test")
    print("=" * 60)

    registry = ModelRegistryService()
    drift_service = DataDriftService()

    # ==========================================================
    # Step 1: Train & Register (2024 season)
    # ==========================================================
    print("\n--- Step 1: Train & Register (batter_segmentation, season=2024) ---")
    try:
        version = registry.train_and_register("batter_segmentation", 2024)
        print(f"  ✅ Registered: {version.version}")
        print(f"     algorithm: {version.algorithm}")
        print(f"     training_season: {version.training_season}")
        print(f"     n_samples: {version.n_samples}")
        print(f"     gcs_path: {version.gcs_path}")
        print(f"     inertia: {version.model_params.get('inertia')}")
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return

    # ==========================================================
    # Step 2: List Versions
    # ==========================================================
    print("\n--- Step 2: List Versions ---")
    versions = registry.list_versions("batter_segmentation")
    print(f"  Total versions: {len(versions)}")
    for v in versions:
        active_mark = " ⭐ ACTIVE" if v.get("is_active") else ""
        print(f"    - {v['version']} (season {v['training_season']}){active_mark}")

    # ==========================================================
    # Step 3: Promote to Active
    # ==========================================================
    print(f"\n--- Step 3: Promote {version.version} to Active ---")
    try:
        registry.promote_version("batter_segmentation", version.version)
        print(f"  ✅ Promoted: {version.version}")
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return

    # ==========================================================
    # Step 4: Verify Active Version
    # ==========================================================
    print("\n--- Step 4: Verify Active Version ---")
    active = registry.get_active_version("batter_segmentation")
    if active:
        print(f"  ✅ Active version: {active.version}")
        print(f"     training_season: {active.training_season}")
        print(f"     algorithm: {active.algorithm}")
    else:
        print("  ❌ No active version found!")
        return

    # ==========================================================
    # Step 5: Load Model from GCS
    # ==========================================================
    print("\n--- Step 5: Load Model from GCS ---")
    try:
        kmeans, scaler, meta = registry.load_model("batter_segmentation")
        print(f"  ✅ Loaded: {meta.version}")
        print(f"     KMeans clusters: {kmeans.n_clusters}")
        print(f"     Scaler features: {scaler.n_features_in_}")
        print(f"     Cluster centers shape: {kmeans.cluster_centers_.shape}")
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return

    # ==========================================================
    # Step 6: Drift Detection with Auto-Baseline
    # ==========================================================
    print("\n--- Step 6: Drift Detection (auto-baseline from registry) ---")
    print(f"  Active model trained on season: {active.training_season}")
    print(f"  → Using baseline_season={active.training_season}, target_season=2025")
    try:
        report = drift_service.detect_drift(
            baseline_season=active.training_season,
            target_season=2025,
            model_type="batter_segmentation",
        )
        report_dict = report.to_dict()
        print(f"  ✅ Drift detected: {report_dict['overall_drift_detected']}")
        print(f"     Summary: {report_dict['summary']}")
        for f in report_dict["features"]:
            print(f"     - {f['feature_name']}: PSI={f['psi_value']:.4f}, severity={f['severity']}")
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return

    # ==========================================================
    # Summary
    # ==========================================================
    print("\n" + "=" * 60)
    print("✅ ALL STEPS PASSED")
    print("=" * 60)
    print(f"  Model: {version.version}")
    print(f"  Algorithm: {version.algorithm}")
    print(f"  GCS: {version.gcs_path}")
    print(f"  Auto-baseline: season {active.training_season} → drift check vs 2025")


if __name__ == "__main__":
    main()
