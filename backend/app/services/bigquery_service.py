from google.cloud import bigquery
import os # 環境変数を読み込むために追加
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv('GCP_PROJECT_ID')

# BigQueryクライアントを初期化
# GOOGLE_APPLICATION_CREDENTIALS 環境変数、またはデフォルトの認証情報が利用されます。
# 明示的にプロジェクトIDを指定する場合は、project='your-gcp-project-id'を追加
client = bigquery.Client(project=PROJECT_ID)

# bigquery_service.pyはBigQueryクライアントのインスタンスを提供する役割
# このファイル自体には、個別のデータ取得ロジックは含めず、他のサービス層ファイルからインポートして利用します。