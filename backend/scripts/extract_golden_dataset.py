import os
import json
from datetime import datetime
from backend.app.services.bigquery_service import client, PROJECT_ID
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PENDING_FILE = "backend/tests/pending_review.json"


def extract_bad_queries():
    """BigQuery から bad 評価のクエリを抽出し、レビュー待ちファイルに出力する"""
    query = f"""
        SELECT 
            request_id,
            user_query,
            parsed_query_type,
            parsed_player_name,
            parsed_season,
            feedback_category,
            feedback_reason
        FROM (
            SELECT 
                request_id,
                MAX(user_query) OVER(PARTITION BY request_id) as user_query,
                MAX(parsed_query_type) OVER(PARTITION BY request_id) as parsed_query_type,
                MAX(parsed_player_name) OVER(PARTITION BY request_id) as parsed_player_name,
                MAX(parsed_season) OVER(PARTITION BY request_id) as parsed_season,
                MAX(feedback_category) OVER(PARTITION BY request_id) as feedback_category,
                MAX(feedback_reason) OVER(PARTITION BY request_id) as feedback_reason,
                user_rating
            FROM `{PROJECT_ID}.mlb_analytics_dash_25.llm_interaction_logs`
            WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
            QUALIFY ROW_NUMBER() OVER(PARTITION BY request_id ORDER BY timestamp DESC) = 1
        )
        WHERE user_rating = 'bad'
          AND user_query IS NOT NULL
          AND user_query != '[FEEDBACK_UPDATE]'
    """
    results = list(client.query(query).result())
    logger.info(f"Found {len(results)} bad-rated queries")

    # Read existing pendings if exists
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, 'r', encoding='utf-8') as f:
            pending = json.load(f)
    else:
        pending = {"pending_cases": []}
    
    # Check duplicates
    existing_ids = {c["request_id"] for c in pending["pending_cases"]}

    added = 0
    for row in results:
        if row.request_id in existing_ids:
            continue

        pending["pending_cases"].append({
            "request_id": row.request_id,
            "query": row.user_query,
            "feedback_category": row.feedback_category,
            "feedback_reason": row.feedback_reason,
            "llm_parsed": {
                "query_type": row.parsed_query_type,
                "player_name": row.parsed_player_name,
                "season": row.parsed_season
            },
            "correct_expected": {
                "query_type": "TODO",
                "metrics_contains": ["TODO"],
                "name": "TODO",
                "season": None
            },
            "reviewed": False
        })
        added += 1
    
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(pending, f, indent=4, ensure_ascii=False)
    
    logger.info(f"Added {added} new cases to {PENDING_FILE}")
    logger.info(f"Total pending: {len(pending['pending_cases'])}")

if __name__ == "__main__":
    extract_bad_queries()