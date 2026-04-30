FROM python:3.11-slim

WORKDIR /app

# Python 依存関係（dbt-bigquery / dbt-metricflow / fastapi 等）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# submodule で取得した dbt プロジェクト一式をコピー（mlb-analytics-data-dbt）
COPY dbt_project ./dbt_project

# diamond-lens 側で管理する Cloud Run 用 profiles.yml を dbt_project 内に配置
# （submodule の profiles.example.yml はテンプレートなので使わない）
COPY profiles.yml ./dbt_project/profiles.yml

# サーバーコード
COPY server.py .

# dbt は profile を DBT_PROFILES_DIR から読むので dbt_project 直下に置く
ENV DBT_PROJECT_DIR=/app/dbt_project
ENV DBT_PROFILES_DIR=/app/dbt_project

# dbt パッケージ依存関係を解決（packages.yml の dbt_utils 等）
# BigQuery 接続不要の操作なのでビルド時に実行可能
RUN dbt deps --project-dir /app/dbt_project

EXPOSE 8080
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
