# =============================================================================
# PHANTOM: AI Honeypot Deception System — Terraform Infrastructure
# Google Cloud Project: phantom-hack2skill
# =============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# -----------------------------------------------------------------------------
# Enable Required APIs
# -----------------------------------------------------------------------------
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "artifactregistry.googleapis.com",
    "aiplatform.googleapis.com",
    "firebase.googleapis.com",
    "firebasehosting.googleapis.com",
    "cloudscheduler.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

# -----------------------------------------------------------------------------
# Artifact Registry — Docker Image Repository
# -----------------------------------------------------------------------------
resource "google_artifact_registry_repository" "phantom" {
  location      = var.region
  repository_id = "phantom-images"
  format        = "DOCKER"
  description   = "PHANTOM honeypot Docker images"

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# Cloud Storage — Report PDFs
# -----------------------------------------------------------------------------
resource "google_storage_bucket" "reports" {
  name          = "${var.project_id}-phantom-reports"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# Firestore Database (Native Mode)
# -----------------------------------------------------------------------------
resource "google_firestore_database" "phantom" {
  name        = "(default)"
  location_id = var.firestore_location
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# Pub/Sub Topics
# -----------------------------------------------------------------------------
resource "google_pubsub_topic" "attacker_commands" {
  name = "attacker-commands"
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "new_session" {
  name = "new-session"
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "rl_decisions" {
  name = "rl-decisions"
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "attacker_disconnect" {
  name = "attacker-disconnect"
  depends_on = [google_project_service.apis]
}

resource "google_pubsub_topic" "simulation_events" {
  name = "simulation-events"
  depends_on = [google_project_service.apis]
}

# Dead letter topic for failed messages
resource "google_pubsub_topic" "dead_letter" {
  name = "phantom-dead-letter"
  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# Service Account for Cloud Run Services
# -----------------------------------------------------------------------------
resource "google_service_account" "phantom_runner" {
  account_id   = "phantom-runner"
  display_name = "PHANTOM Cloud Run Service Account"
}

# Grant roles to the service account
resource "google_project_iam_member" "phantom_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.phantom_runner.email}"
}

resource "google_project_iam_member" "phantom_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.phantom_runner.email}"
}

resource "google_project_iam_member" "phantom_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.phantom_runner.email}"
}

resource "google_project_iam_member" "phantom_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.phantom_runner.email}"
}

resource "google_project_iam_member" "phantom_vertex" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.phantom_runner.email}"
}

resource "google_project_iam_member" "phantom_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.phantom_runner.email}"
}

# -----------------------------------------------------------------------------
# Cloud Run Services
# -----------------------------------------------------------------------------
locals {
  image_base = "${var.region}-docker.pkg.dev/${var.project_id}/phantom-images"
}

# Layer 1: Flask Honeypot
resource "google_cloud_run_v2_service" "layer1_honeypot" {
  name     = "phantom-layer1-honeypot"
  location = var.region

  template {
    service_account = google_service_account.phantom_runner.email

    scaling {
      min_instance_count = 1
      max_instance_count = 5
    }

    containers {
      image = "${local.image_base}/layer1-honeypot:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "LAYER2_URL"
        value = "https://phantom-layer2-bible-${var.cloud_run_hash}.a.run.app"
      }

      ports {
        container_port = 8080
      }
    }

    timeout = "540s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.apis]
}

# Layer 2: Company Bible Generator
resource "google_cloud_run_v2_service" "layer2_bible" {
  name     = "phantom-layer2-bible"
  location = var.region

  template {
    service_account = google_service_account.phantom_runner.email

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      image = "${local.image_base}/layer2-bible:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }

      ports {
        container_port = 8080
      }
    }

    timeout = "540s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.apis]
}

# Layer 3: RL Agent
resource "google_cloud_run_v2_service" "layer3_rl" {
  name     = "phantom-layer3-rl"
  location = var.region

  template {
    service_account = google_service_account.phantom_runner.email

    scaling {
      min_instance_count = 1
      max_instance_count = 5
    }

    containers {
      image = "${local.image_base}/layer3-rl:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }

      ports {
        container_port = 8080
      }
    }

    timeout = "60s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.apis]
}

# Layer 4: Behavioral Analysis
resource "google_cloud_run_v2_service" "layer4_analysis" {
  name     = "phantom-layer4-analysis"
  location = var.region

  template {
    service_account = google_service_account.phantom_runner.email

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      image = "${local.image_base}/layer4-analysis:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }

      ports {
        container_port = 8080
      }
    }

    timeout = "540s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.apis]
}

# Layer 5: Report Generator
resource "google_cloud_run_v2_service" "layer5_reports" {
  name     = "phantom-layer5-reports"
  location = var.region

  template {
    service_account = google_service_account.phantom_runner.email

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      image = "${local.image_base}/layer5-reports:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "REPORTS_BUCKET"
        value = google_storage_bucket.reports.name
      }

      ports {
        container_port = 8080
      }
    }

    timeout = "540s"
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# Make Cloud Run services publicly accessible (honeypot must be public)
# -----------------------------------------------------------------------------
resource "google_cloud_run_v2_service_iam_member" "layer1_public" {
  name     = google_cloud_run_v2_service.layer1_honeypot.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "layer5_public" {
  name     = google_cloud_run_v2_service.layer5_reports.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# -----------------------------------------------------------------------------
# Pub/Sub Push Subscriptions → Cloud Run
# -----------------------------------------------------------------------------
resource "google_pubsub_subscription" "commands_to_rl" {
  name  = "attacker-commands-to-rl"
  topic = google_pubsub_topic.attacker_commands.id

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.layer3_rl.uri}/api/pubsub/command"
    oidc_token {
      service_account_email = google_service_account.phantom_runner.email
    }
  }

  ack_deadline_seconds       = 30
  message_retention_duration = "600s"

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }
}

resource "google_pubsub_subscription" "session_to_bible" {
  name  = "new-session-to-bible"
  topic = google_pubsub_topic.new_session.id

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.layer2_bible.uri}/api/pubsub/new-session"
    oidc_token {
      service_account_email = google_service_account.phantom_runner.email
    }
  }

  ack_deadline_seconds       = 60
  message_retention_duration = "600s"

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }
}

resource "google_pubsub_subscription" "rl_to_analysis" {
  name  = "rl-decisions-to-analysis"
  topic = google_pubsub_topic.rl_decisions.id

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.layer4_analysis.uri}/api/pubsub/rl-decision"
    oidc_token {
      service_account_email = google_service_account.phantom_runner.email
    }
  }

  ack_deadline_seconds       = 60
  message_retention_duration = "600s"

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }
}

resource "google_pubsub_subscription" "disconnect_to_reports" {
  name  = "attacker-disconnect-to-reports"
  topic = google_pubsub_topic.attacker_disconnect.id

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.layer5_reports.uri}/api/pubsub/disconnect"
    oidc_token {
      service_account_email = google_service_account.phantom_runner.email
    }
  }

  ack_deadline_seconds       = 120
  message_retention_duration = "600s"

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }
}
