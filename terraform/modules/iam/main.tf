variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "service_account_id" {
  description = "Service account ID"
  type        = string
}

variable "display_name" {
  description = "Service account display name"
  type        = string
}

variable "description" {
  description = "Service account description"
  type        = string
  default     = ""
}

variable "project_roles" {
  description = "List of project-level roles to assign"
  type        = list(string)
  default     = []
}

resource "google_service_account" "sa" {
  project      = var.project_id
  account_id   = var.service_account_id
  display_name = var.display_name
  description  = var.description
}

resource "google_project_iam_member" "sa_roles" {
  for_each = toset(var.project_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.sa.email}"
}

output "service_account_email" {
  description = "Service account email"
  value       = google_service_account.sa.email
}

output "service_account_name" {
  description = "Service account name"
  value       = google_service_account.sa.name
}

output "service_account_id" {
  description = "Service account ID"
  value       = google_service_account.sa.account_id
}
