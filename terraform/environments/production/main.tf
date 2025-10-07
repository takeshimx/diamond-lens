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

# Secrets (既存のシークレットをimportする想定)
module "gemini_api_key" {
  source = "../../modules/secrets"

  project_id            = var.project_id
  secret_id             = "GEMINI_API_KEY"
  replication_locations = []
  # secret_data は指定しない（既存の値を使う）
}

module "vite_app_password" {
  source = "../../modules/secrets"

  project_id            = var.project_id
  secret_id             = "VITE_APP_PASSWORD"
  replication_locations = []
  # secret_data は指定しない（既存の値を使う）
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
    GEMINI_API_KEY = {
      secret_name = module.gemini_api_key.secret_id
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

# Outputs
output "backend_url" {
  description = "Backend Cloud Run URL"
  value       = module.backend_cloud_run.service_url
}

output "frontend_url" {
  description = "Frontend Cloud Run URL"
  value       = module.frontend_cloud_run.service_url
}
