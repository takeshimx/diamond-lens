# 既存のCloud Runサービス名に合わせた設定ファイル
# このファイルは main.tf の代替として、既存環境との互換性を保つために使用

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "diamond-lens-terraform-state"
    prefix = "production/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "tksm-dash-test-25"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-northeast1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "notification_email" {
  description = "Email address for monitoring alerts"
  type        = string
  default     = ""
}

# BigQuery Dataset (既存をimport)
module "bigquery_dataset" {
  source = "../../modules/bigquery"

  project_id                 = var.project_id
  dataset_id                 = "mlb_analytics_dash_25"
  location                   = "asia-northeast1"
  description                = "MLB statistics dataset"
  delete_contents_on_destroy = false
}

# Cloud Run - Backend (既存のサービス名に合わせる)
module "backend_cloud_run" {
  source = "../../modules/cloud-run"

  project_id            = var.project_id
  region                = var.region
  service_name          = "mlb-diamond-lens-api"
  image                 = "gcr.io/${var.project_id}/mlb-diamond-lens-api:latest"
  service_account_email = "907924272679-compute@developer.gserviceaccount.com"
  port                  = 8080
  cpu                   = "1"
  memory                = "512Mi"
  min_instances         = 0
  max_instances         = 20

  env_vars = {
    GCP_PROJECT_ID                   = var.project_id
    BIGQUERY_DATASET_ID              = "mlb_analytics_dash_25"
    BIGQUERY_BATTING_STATS_TABLE_ID  = "fact_batting_stats_with_risp"
    BIGQUERY_PITCHING_STATS_TABLE_ID = "fact_pitching_stats"
    ENVIRONMENT                      = var.environment
  }

  secrets = {
    GEMINI_API_KEY_V2 = {
      secret_name = "GEMINI_API_KEY_V2"
      version     = "latest"
    }
    DISCORD_WEBHOOK_URL_LAD = {
      secret_name = "DISCORD_WEBHOOK_URL_LAD"
      version     = "latest"
    }
  }

  allow_unauthenticated = true
}

# Cloud Run - Frontend (既存のサービス名に合わせる)
module "frontend_cloud_run" {
  source = "../../modules/cloud-run"

  project_id            = var.project_id
  region                = var.region
  service_name          = "mlb-diamond-lens-frontend"
  image                 = "gcr.io/${var.project_id}/mlb-diamond-lens-frontend:latest"
  service_account_email = "907924272679-compute@developer.gserviceaccount.com"
  port                  = 8080
  cpu                   = "1"
  memory                = "512Mi"
  min_instances         = 0
  max_instances         = 20

  env_vars = {
    VITE_API_URL = module.backend_cloud_run.service_url
    ENVIRONMENT  = var.environment
  }

  allow_unauthenticated = true
}

# ============================================================
# Secret Manager: Discord Webhook URL (LAD サマリー投稿用)
# 値は手動で登録: gcloud secrets versions add DISCORD_WEBHOOK_URL_LAD --data-file=-
# ============================================================
resource "google_secret_manager_secret" "discord_webhook_lad" {
  project   = var.project_id
  secret_id = "DISCORD_WEBHOOK_URL_LAD"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  labels = {
    managed_by = "terraform"
  }
}

# ============================================================
# Cloud Scheduler: LAD 試合終了サマリー自動投稿
# Scheduler 専用サービスアカウント
# ============================================================
resource "google_service_account" "lad_summary_scheduler_sa" {
  project      = var.project_id
  account_id   = "lad-summary-scheduler"
  display_name = "LAD Game Summary Cloud Scheduler SA"
}

resource "google_cloud_run_v2_service_iam_member" "lad_scheduler_invoker" {
  project  = var.project_id
  location = var.region
  name     = "mlb-diamond-lens-api"
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.lad_summary_scheduler_sa.email}"
}

# Day game 終了後トリガー (JST 9:00 = UTC 00:00)
resource "google_cloud_scheduler_job" "lad_summary_day_game" {
  project   = var.project_id
  region    = var.region
  name      = "lad-summary-day-game"
  schedule  = "0 0 * * *"
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${module.backend_cloud_run.service_url}/api/v1/internal/summary/trigger"

    oidc_token {
      service_account_email = google_service_account.lad_summary_scheduler_sa.email
      audience              = module.backend_cloud_run.service_url
    }
  }

  retry_config {
    retry_count          = 1
    min_backoff_duration = "5s"
  }

  depends_on = [google_cloud_run_v2_service_iam_member.lad_scheduler_invoker]
}

# Night game 終了後トリガー (JST 15:00 = UTC 06:00)
resource "google_cloud_scheduler_job" "lad_summary_night_game" {
  project   = var.project_id
  region    = var.region
  name      = "lad-summary-night-game"
  schedule  = "30 5 * * *"
  time_zone = "UTC"

  http_target {
    http_method = "POST"
    uri         = "${module.backend_cloud_run.service_url}/api/v1/internal/summary/trigger"

    oidc_token {
      service_account_email = google_service_account.lad_summary_scheduler_sa.email
      audience              = module.backend_cloud_run.service_url
    }
  }

  retry_config {
    retry_count          = 1
    min_backoff_duration = "5s"
  }

  depends_on = [google_cloud_run_v2_service_iam_member.lad_scheduler_invoker]
}

# Monitoring & Alerting
module "monitoring" {
  source = "../../modules/monitoring"

  project_id            = var.project_id
  region                = var.region
  backend_service_name  = "mlb-diamond-lens-api"
  frontend_service_name = "mlb-diamond-lens-frontend"
  notification_email    = var.notification_email
}

# Outputs
output "backend_url" {
  description = "Backend Cloud Run URL"
  value       = module.backend_cloud_run.service_url
}

output "frontend_url" {
  description = "Frontend Cloud Run URL"
  value       = module.frontend_cloud_run.service_url
}

# Uptime checks disabled by default - uncomment if needed
# output "backend_uptime_check_id" {
#   description = "Backend uptime check ID"
#   value       = module.monitoring.backend_uptime_check_id
# }
#
# output "frontend_uptime_check_id" {
#   description = "Frontend uptime check ID"
#   value       = module.monitoring.frontend_uptime_check_id
# }

output "alert_policy_ids" {
  description = "Monitoring alert policy IDs"
  value       = module.monitoring.alert_policy_ids
}
