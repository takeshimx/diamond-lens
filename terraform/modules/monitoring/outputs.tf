# Uptime checks are disabled by default (commented out in uptime_checks.tf)
# Uncomment these outputs if you enable uptime checks
# output "backend_uptime_check_id" {
#   description = "Backend uptime check ID"
#   value       = google_monitoring_uptime_check_config.backend_health.uptime_check_id
# }
#
# output "frontend_uptime_check_id" {
#   description = "Frontend uptime check ID"
#   value       = google_monitoring_uptime_check_config.frontend_health.uptime_check_id
# }

output "alert_policy_ids" {
  description = "List of alert policy IDs"
  value = [
    # google_monitoring_alert_policy.backend_down.id,  # Disabled (requires uptime checks)
    # google_monitoring_alert_policy.frontend_down.id,  # Disabled (requires uptime checks)
    google_monitoring_alert_policy.high_memory.id,
    google_monitoring_alert_policy.high_cpu.id
  ]
}

output "notification_channel_id" {
  description = "Notification channel ID (if email configured)"
  value       = var.notification_email != "" ? google_monitoring_notification_channel.email[0].id : ""
}

output "dashboard_id" {
  description = "Monitoring dashboard ID"
  value       = google_monitoring_dashboard.main.id
}
