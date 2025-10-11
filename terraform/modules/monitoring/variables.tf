variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-northeast1"
}

variable "backend_service_name" {
  description = "Backend Cloud Run service name"
  type        = string
  default     = "mlb-diamond-lens-api"
}

variable "frontend_service_name" {
  description = "Frontend Cloud Run service name"
  type        = string
  default     = "mlb-diamond-lens-frontend"
}

variable "notification_email" {
  description = "Email address for alerts"
  type        = string
  default     = ""
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications (optional)"
  type        = string
  default     = ""
  sensitive   = true
}
