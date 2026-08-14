"""
pytest 共通設定。

CI には GCP 認証情報も .env も存在しないため、settings の必須項目にダミー値を注入する。
実 GCP へのアクセスが必要なテストは、各テストファイル側で skip マークを付ける方針。
"""
import os
import sys
from pathlib import Path

# backend/ をパスに追加（tests/ から app.* を import するため）
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))
# backend の親（プロジェクトルート）も追加（backend.app.* 形式の import に対応）
sys.path.insert(0, str(BACKEND_ROOT.parent))

# GCP 認証を絶対に走らせない。空文字を明示して ADC 探索を止める。
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
