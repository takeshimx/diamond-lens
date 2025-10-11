# Notification Channel (Email)
resource "google_monitoring_notification_channel" "email" {
  count        = var.notification_email != "" ? 1 : 0
  display_name = "Email Notification Channel"
  type         = "email"

  labels = {
    email_address = var.notification_email
  }
}

# Alert Policy: Backend API Down
resource "google_monitoring_alert_policy" "backend_down" {
  display_name = "MLB API Down Alert"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Backend API Uptime Check Failed"

    condition_threshold {
      filter          = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\" AND metric.label.check_id=\"${google_monitoring_uptime_check_config.backend_health.uptime_check_id}\""
      duration        = "60s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_FRACTION_TRUE"
      }
    }
  }

  notification_channels = var.notification_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "1800s"  # 30分後に自動クローズ
  }

  documentation {
    content   = <<-EOT
      MLB Diamond Lens API is down!

      **Action Required:**
      1. Check Cloud Run logs: https://console.cloud.google.com/run?project=${var.project_id}
      2. Verify /health endpoint
      3. Check recent deployments

      **Runbook:** See docs/INCIDENT_RESPONSE.md
    EOT
    mime_type = "text/markdown"
  }
}

# Alert Policy: Frontend Down
resource "google_monitoring_alert_policy" "frontend_down" {
  display_name = "MLB Frontend Down Alert"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Frontend Uptime Check Failed"

    condition_threshold {
      filter          = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\" AND metric.label.check_id=\"${google_monitoring_uptime_check_config.frontend_health.uptime_check_id}\""
      duration        = "60s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_FRACTION_TRUE"
      }
    }
  }

  notification_channels = var.notification_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "MLB Diamond Lens Frontend is down. Check Cloud Run service status."
    mime_type = "text/markdown"
  }
}

# Alert Policy: High Memory Usage
resource "google_monitoring_alert_policy" "high_memory" {
  display_name = "High Memory Usage (Backend)"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Memory utilization > 80%"

    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/container/memory/utilizations\" AND resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"${var.backend_service_name}\""
      duration        = "300s"  # 5分間継続
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = var.notification_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  documentation {
    content   = "Backend memory usage is high. Consider increasing memory limits or investigating memory leaks."
    mime_type = "text/markdown"
  }
}

# Alert Policy: High CPU Usage
resource "google_monitoring_alert_policy" "high_cpu" {
  display_name = "High CPU Usage (Backend)"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "CPU utilization > 80%"

    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/container/cpu/utilizations\" AND resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"${var.backend_service_name}\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = var.notification_email != "" ? [google_monitoring_notification_channel.email[0].id] : []

  documentation {
    content   = "Backend CPU usage is high. Consider increasing CPU or optimizing queries."
    mime_type = "text/markdown"
  }
}
