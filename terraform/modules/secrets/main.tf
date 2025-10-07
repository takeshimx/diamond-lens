variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "secret_id" {
  description = "Secret ID"
  type        = string
}

variable "secret_data" {
  description = "Secret data (sensitive)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "replication_locations" {
  description = "Locations for secret replication"
  type        = list(string)
  default     = ["asia-northeast1"]
}

resource "google_secret_manager_secret" "secret" {
  project   = var.project_id
  secret_id = var.secret_id

  replication {
    dynamic "auto" {
      for_each = length(var.replication_locations) == 0 ? [1] : []
      content {}
    }

    dynamic "user_managed" {
      for_each = length(var.replication_locations) > 0 ? [1] : []
      content {
        dynamic "replicas" {
          for_each = var.replication_locations
          content {
            location = replicas.value
          }
        }
      }
    }
  }

  labels = {
    managed_by = "terraform"
  }
}

resource "google_secret_manager_secret_version" "secret_version" {
  count = var.secret_data != "" ? 1 : 0

  secret      = google_secret_manager_secret.secret.id
  secret_data = var.secret_data
}

output "secret_id" {
  description = "Secret ID"
  value       = google_secret_manager_secret.secret.secret_id
}

output "secret_name" {
  description = "Secret name"
  value       = google_secret_manager_secret.secret.name
}
