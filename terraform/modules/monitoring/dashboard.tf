resource "google_monitoring_dashboard" "main" {
  dashboard_json = jsonencode({
    displayName = "MLB Diamond Lens - Service Health"

    mosaicLayout = {
      columns = 12

      tiles = [
        # Uptime widgets removed (uptime checks disabled by default)
        # Uncomment uptime_checks.tf to re-enable these widgets

        # API Latency
        {
          width  = 12
          height = 4
          yPos   = 0
          widget = {
            title = "API Request Latency"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"custom.googleapis.com/diamond-lens/api/latency\" resource.type=\"generic_task\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_MEAN"
                      crossSeriesReducer = "REDUCE_PERCENTILE_95"
                      groupByFields      = ["metric.label.endpoint"]
                    }
                  }
                }
                plotType = "LINE"
                targetAxis = "Y1"
              }]
              yAxis = {
                label = "Latency (ms)"
                scale = "LINEAR"
              }
            }
          }
        },

        # Memory Utilization
        {
          width  = 6
          height = 4
          yPos   = 4
          widget = {
            title = "Memory Utilization"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"run.googleapis.com/container/memory/utilizations\" resource.type=\"cloud_run_revision\" resource.label.service_name=\"${var.backend_service_name}\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_PERCENTILE_99"
                      crossSeriesReducer = "REDUCE_MEAN"
                    }
                  }
                }
                plotType = "LINE"
                targetAxis = "Y1"
              }]
              yAxis = {
                label = "Utilization"
                scale = "LINEAR"
              }
              thresholds = [{
                value = 0.8
              }]
            }
          }
        },

        # CPU Utilization
        {
          width  = 6
          height = 4
          xPos   = 6
          yPos   = 4
          widget = {
            title = "CPU Utilization"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"run.googleapis.com/container/cpu/utilizations\" resource.type=\"cloud_run_revision\" resource.label.service_name=\"${var.backend_service_name}\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_PERCENTILE_99"
                      crossSeriesReducer = "REDUCE_MEAN"
                    }
                  }
                }
                plotType = "LINE"
                targetAxis = "Y1"
              }]
              yAxis = {
                label = "Utilization"
                scale = "LINEAR"
              }
              thresholds = [{
                value = 0.8
              }]
            }
          }
        },

        # Instance Count
        {
          width  = 12
          height = 4
          yPos   = 8
          widget = {
            title = "Active Instances"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"run.googleapis.com/container/instance_count\" resource.type=\"cloud_run_revision\" resource.label.service_name=\"${var.backend_service_name}\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_MEAN"
                        crossSeriesReducer = "REDUCE_SUM"
                      }
                    }
                  }
                  plotType = "LINE"
                  targetAxis = "Y1"
                  legendTemplate = "Backend"
                },
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "metric.type=\"run.googleapis.com/container/instance_count\" resource.type=\"cloud_run_revision\" resource.label.service_name=\"${var.frontend_service_name}\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_MEAN"
                        crossSeriesReducer = "REDUCE_SUM"
                      }
                    }
                  }
                  plotType = "LINE"
                  targetAxis = "Y1"
                  legendTemplate = "Frontend"
                }
              ]
              yAxis = {
                label = "Instances"
                scale = "LINEAR"
              }
            }
          }
        }
      ]
    }
  })
}
