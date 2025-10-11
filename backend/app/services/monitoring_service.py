"""
Monitoring service for custom metrics and application performance tracking
Exports metrics to Google Cloud Monitoring
"""

import os
import time
from typing import Optional
from google.cloud import monitoring_v3
from google.api import metric_pb2 as ga_metric


class MonitoringService:
    """
    Service for recording custom metrics to Google Cloud Monitoring

    Key metrics tracked:
    - API request latency (ms)
    - API error rate
    - Query processing time
    - BigQuery query latency
    """

    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.client: Optional[monitoring_v3.MetricServiceClient] = None
        self.project_name: Optional[str] = None

        # Initialize only if project_id is set
        if self.project_id:
            try:
                self.client = monitoring_v3.MetricServiceClient()
                self.project_name = f"projects/{self.project_id}"
            except Exception as e:
                print(f"Warning: Failed to initialize monitoring client: {e}")
                self.client = None

    def _write_time_series(self, metric_type: str, value: float, labels: dict = None):
        """Write a time series data point to Cloud Monitoring"""
        if not self.client or not self.project_name:
            return

        try:
            series = monitoring_v3.TimeSeries()
            series.metric.type = f"custom.googleapis.com/diamond-lens/{metric_type}"

            # Add labels if provided
            if labels:
                for key, val in labels.items():
                    series.metric.labels[key] = str(val)

            series.resource.type = "generic_task"
            series.resource.labels["project_id"] = self.project_id
            series.resource.labels["location"] = os.getenv("GCP_REGION", "asia-northeast1")
            series.resource.labels["namespace"] = "mlb-diamond-lens"
            series.resource.labels["job"] = "diamond-lens-api"
            series.resource.labels["task_id"] = "api"

            # Create data point
            now = time.time()
            seconds = int(now)
            nanos = int((now - seconds) * 10**9)
            interval = monitoring_v3.TimeInterval(
                {"end_time": {"seconds": seconds, "nanos": nanos}}
            )
            point = monitoring_v3.Point(
                {"interval": interval, "value": {"double_value": value}}
            )
            series.points = [point]

            # Write to Cloud Monitoring
            self.client.create_time_series(name=self.project_name, time_series=[series])

        except Exception as e:
            # Don't fail the request if monitoring fails
            print(f"Warning: Failed to write metric {metric_type}: {e}")

    def record_api_latency(self, endpoint: str, latency_ms: float, status_code: int):
        """
        Record API endpoint latency

        Args:
            endpoint: API endpoint path
            latency_ms: Request latency in milliseconds
            status_code: HTTP status code
        """
        self._write_time_series(
            metric_type="api/latency",
            value=latency_ms,
            labels={
                "endpoint": endpoint,
                "status_code": str(status_code),
            },
        )

    def record_api_error(self, endpoint: str, error_type: str):
        """
        Record API error occurrence

        Args:
            endpoint: API endpoint path
            error_type: Type of error (validation_error, llm_error, bigquery_error, etc.)
        """
        self._write_time_series(
            metric_type="api/errors",
            value=1.0,
            labels={
                "endpoint": endpoint,
                "error_type": error_type,
            },
        )

    def record_query_processing_time(self, query_type: str, processing_ms: float):
        """
        Record query processing time

        Args:
            query_type: Type of query (season_batting, season_pitching, etc.)
            processing_ms: Processing time in milliseconds
        """
        self._write_time_series(
            metric_type="query/processing_time",
            value=processing_ms,
            labels={"query_type": query_type},
        )

    def record_bigquery_latency(self, query_type: str, latency_ms: float):
        """
        Record BigQuery query latency

        Args:
            query_type: Type of query
            latency_ms: Query latency in milliseconds
        """
        self._write_time_series(
            metric_type="bigquery/latency",
            value=latency_ms,
            labels={"query_type": query_type},
        )


# Singleton instance
_monitoring_instance: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """Get or create monitoring service instance"""
    global _monitoring_instance
    if _monitoring_instance is None:
        _monitoring_instance = MonitoringService()
    return _monitoring_instance
