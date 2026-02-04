

class MLBAppError(Exception):
    """
    【親クラス】このプロジェクトで起きる「すべてのエラー」の共通ルール。
    これを定義しておくことで、後で「このアプリ独自のエラーだけをキャッチする」
    ということが可能になります。
    """
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DataFetchError(MLBAppError):
    """
    【子クラス】データ取得（BigQueryなど）に特化したエラー。
    """

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error


class AgentReasoningError(MLBAppError):
    """
    AI（エージェント）の思考プロセスやAPI呼び出しで発生したエラー
    """

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error


class DataStructureError(MLBAppError):
    """
    【子クラス】取得したデータの形式が期待と異なる場合のエラー
    """

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error