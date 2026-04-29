FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DBT_PROJECT_DIR=/app
ENV DBT_PROFILES_DIR=/app

# dbt パッケージ依存関係を解決（packages.yml の dbt_utils 等）
# BigQuery 接続不要の操作なのでビルド時に実行可能
RUN dbt deps --project-dir /app

EXPOSE 8080
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
