# Backend API Uptime Check
resource "google_monitoring_uptime_check_config" "backend_health" {
  display_name = "MLB API Health Check"
  timeout      = "20s"  # Cold start考慮（min_instances=0の場合、起動に5-10秒）
  period       = "60s"  # 1分ごとにチェック

  http_check {
    path         = "/health"
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "${var.backend_service_name}-${data.google_project.project.number}.${var.region}.run.app"
    }
  }

  # 3つの地域からチェック（信頼性向上）
  selected_regions = ["USA", "EUROPE", "ASIA_PACIFIC"]
}

# Frontend Uptime Check
resource "google_monitoring_uptime_check_config" "frontend_health" {
  display_name = "MLB Frontend Health Check"
  timeout      = "20s"  # Cold start考慮（min_instances=0の場合、起動に5-10秒）
  period       = "60s"

  http_check {
    path         = "/"
    port         = "443"
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = "${var.frontend_service_name}-${data.google_project.project.number}.${var.region}.run.app"
    }
  }

  selected_regions = ["USA", "EUROPE", "ASIA_PACIFIC"]
}

# Project data source
data "google_project" "project" {
  project_id = var.project_id
}
