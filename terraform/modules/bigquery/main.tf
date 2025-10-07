variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
}

variable "location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "asia-northeast1"
}

variable "description" {
  description = "Dataset description"
  type        = string
  default     = ""
}

variable "delete_contents_on_destroy" {
  description = "Delete all tables when dataset is destroyed"
  type        = bool
  default     = false
}

resource "google_bigquery_dataset" "dataset" {
  project       = var.project_id
  dataset_id    = var.dataset_id
  friendly_name = var.dataset_id
  description   = var.description
  location      = var.location

  delete_contents_on_destroy = var.delete_contents_on_destroy

  labels = {
    managed_by = "terraform"
    environment = "production"
  }
}

output "dataset_id" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.dataset.dataset_id
}

output "dataset_self_link" {
  description = "BigQuery dataset self link"
  value       = google_bigquery_dataset.dataset.self_link
}
