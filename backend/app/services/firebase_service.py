import firebase_admin
from firebase_admin import credentials, auth
import os
from backend.app.utils.structured_logger import get_logger

logger = get_logger("firebase")

_firebase_app = None


def init_firebase():
    """Firebase Admin SDKを初期化（シングルトン）"""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path:
        cred = credentials.Certificate(cred_path)
    else:
        # Cloud Run ではデフォルトの認証情報を使用
        cred = credentials.ApplicationDefault()

    _firebase_app = firebase_admin.initialize_app(cred, {
        "projectId": os.getenv("GCP_PROJECT_ID")
    })
    logger.info("Firebase Admin SDK initialized")
    return _firebase_app


def verify_firebase_token(id_token: str) -> dict:
    """Firebase ID トークンを検証し、デコード結果を返す"""
    init_firebase()
    decoded_token = auth.verify_id_token(id_token)
    return decoded_token
