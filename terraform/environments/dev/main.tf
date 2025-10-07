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
    prefix = "dev/state"
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
  default     = "dev"
}

# Service Accounts
module "backend_sa" {
  source = "../../modules/iam"

  project_id         = var.project_id
  service_account_id = "diamond-lens-backend-dev"
  display_name       = "Diamond Lens Backend Service Account (Dev)"
  description        = "Service account for Diamond Lens backend Cloud Run service (Dev)"

  project_roles = [
    "roles/bigquery.dataViewer",
    "roles/bigquery.jobUser",
    "roles/secretmanager.secretAccessor",
  ]
}

# Secrets
module "gemini_api_key" {
  source = "../../modules/secrets"

  project_id            = var.project_id
  secret_id             = "gemini-api-key-dev"
  replication_locations = ["asia-northeast1"]
}

# Cloud Run - Backend
module "backend_cloud_run" {
  source = "../../modules/cloud-run"

  project_id            = var.project_id
  region                = var.region
  service_name          = "diamond-lens-backend-dev"
  image                 = "asia-northeast1-docker.pkg.dev/${var.project_id}/diamond-lens/backend:dev"
  service_account_email = module.backend_sa.service_account_email
  port                  = 8000
  cpu                   = "1"
  memory                = "512Mi"
  min_instances         = 0
  max_instances         = 3

  env_vars = {
    GCP_PROJECT_ID                   = var.project_id
    BIGQUERY_DATASET_ID              = "mlb_stats"
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

output "backend_url" {
  description = "Backend Cloud Run URL (Dev)"
  value       = module.backend_cloud_run.service_url
}
