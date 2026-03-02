from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
def _get_session_or_ip(request: Request) -> str:
    """
    セッションIDがあればそれをキーに、なければIPアドレスをキーにする。
    Firebase認証済みユーザーはuser_idをキーにする。
    """
    # 1. Check for Firebase user
    user_id = getattr(request.state, "user_id", None)
    if user_id and user_id != "anonymous":
        return f"user:{user_id}"

    # 2. Check for session ID
    # Note: slowapiはリクエスト処理前に呼ばれるため、bodyは読めない
    session_id = request.headers.get("X-Session-ID")
    if session_id:
        return f"session:{session_id}"

    # 3. Use IP address
    return get_remote_address(request)


# slowapi のデフォルトストレージはインメモリ（memory://）
# Cloud Run は単一コンテナなのでインメモリで十分。Redis不要。
limiter = Limiter(
    key_func=_get_session_or_ip,
    storage_uri="memory://",
    strategy="fixed-window",
)