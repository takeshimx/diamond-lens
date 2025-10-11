resource "google_monitoring_dashboard" "main" {
  dashboard_json = jsonencode({
    displayName = "MLB Diamond Lens - Service Health"

    mosaicLayout = {
      columns = 12

      tiles = [
        # Uptime Check Status
        {
          width  = 6
          height = 4
          widget = {
            title = "Backend API Uptime"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" resource.type=\"uptime_url\" metric.label.check_id=\"${google_monitoring_uptime_check_config.backend_health.uptime_check_id}\""
                  aggregation = {
                    alignmentPeriod    = "60s"
                    perSeriesAligner   = "ALIGN_FRACTION_TRUE"
                    crossSeriesReducer = "REDUCE_MEAN"
                  }
                }
              }
              sparkChartView = {
                sparkChartType = "SPARK_LINE"
              }
            }
          }
        },

        # Frontend Uptime
        {
          width  = 6
          height = 4
          xPos   = 6
          widget = {
            title = "Frontend Uptime"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" resource.type=\"uptime_url\" metric.label.check_id=\"${google_monitoring_uptime_check_config.frontend_health.uptime_check_id}\""
                  aggregation = {
                    alignmentPeriod    = "60s"
                    perSeriesAligner   = "ALIGN_FRACTION_TRUE"
                    crossSeriesReducer = "REDUCE_MEAN"
                  }
                }
              }
              sparkChartView = {
                sparkChartType = "SPARK_LINE"
              }
            }
          }
        },

        # API Latency
        {
          width  = 12
          height = 4
          yPos   = 4
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
          yPos   = 8
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
          yPos   = 8
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
          yPos   = 12
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
