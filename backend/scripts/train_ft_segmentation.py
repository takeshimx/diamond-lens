"""
FT-Transformer セグメンテーションモデル ローカル学習スクリプト

ローカル環境 (torch インストール済み) で FT-Transformer を学習し、
Model Registry (GCS + BigQuery) に登録する。

Usage:
    cd backend
    set PYTHONPATH=..          # Windows
    export PYTHONPATH=..       # Linux/Mac
    python scripts/train_ft_segmentation.py --model_type batter_segmentation_ft --season 2025
    python scripts/train_ft_segmentation.py --model_type pitcher_segmentation_ft --season 2025 --promote
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import argparse
from backend.app.services.model_registry_service import ModelRegistryService


def main():
    parser = argparse.ArgumentParser(description="Train FT-Transformer segmentation model locally")
    parser.add_argument(
        "--model_type",
        choices=["batter_segmentation_ft", "pitcher_segmentation_ft"],
        required=True,
        help="Model type to train",
    )
    parser.add_argument(
        "--season",
        type=int,
        default=2025,
        help="Season year for training data (default: 2025)",
    )
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Automatically promote the trained model to active",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(f"FT-Transformer Training: {args.model_type}")
    print(f"Season: {args.season}")
    print("=" * 60)

    # Check torch availability
    try:
        import torch
        print(f"  PyTorch version: {torch.__version__}")
    except ImportError:
        print("  ERROR: PyTorch is not installed.")
        print("  Install it with: pip install torch")
        sys.exit(1)

    registry = ModelRegistryService()

    # Step 1: Train & Register
    print(f"\n--- Step 1: Train & Register ({args.model_type}, season={args.season}) ---")
    try:
        version = registry.train_and_register(args.model_type, args.season)
        print(f"  Registered: {version.version}")
        print(f"  algorithm: {version.algorithm}")
        print(f"  training_season: {version.training_season}")
        print(f"  n_samples: {version.n_samples}")
        print(f"  gcs_path: {version.gcs_path}")
        print(f"  embedding_dim: {version.model_params.get('embedding_dim')}")
        print(f"  inertia: {version.model_params.get('inertia')}")
    except Exception as e:
        print(f"  Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 2: Promote (optional)
    if args.promote:
        print(f"\n--- Step 2: Promote {version.version} to Active ---")
        try:
            registry.promote_version(args.model_type, version.version)
            print(f"  Promoted: {version.version}")
        except Exception as e:
            print(f"  Failed to promote: {e}")
            sys.exit(1)
    else:
        print(f"\n--- Skipping promote (use --promote to auto-promote) ---")
        print(f"  To promote manually:")
        print(f"    POST /api/v1/model-registry/promote")
        print(f"    body: {{\"model_type\": \"{args.model_type}\", \"version\": \"{version.version}\"}}")

    # Summary
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"  Model: {version.version}")
    print(f"  GCS: {version.gcs_path}")
    if args.promote:
        print(f"  Status: ACTIVE")
    else:
        print(f"  Status: registered (not yet active)")


if __name__ == "__main__":
    main()
