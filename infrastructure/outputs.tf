# =============================================================================
# PHANTOM — Terraform Outputs
# =============================================================================

output "layer1_honeypot_url" {
  description = "Layer 1 Flask Honeypot URL"
  value       = google_cloud_run_v2_service.layer1_honeypot.uri
}

output "layer2_bible_url" {
  description = "Layer 2 Company Bible Generator URL"
  value       = google_cloud_run_v2_service.layer2_bible.uri
}

output "layer3_rl_url" {
  description = "Layer 3 RL Agent URL"
  value       = google_cloud_run_v2_service.layer3_rl.uri
}

output "layer4_analysis_url" {
  description = "Layer 4 Behavioral Analysis URL"
  value       = google_cloud_run_v2_service.layer4_analysis.uri
}

output "layer5_reports_url" {
  description = "Layer 5 Report Generator URL"
  value       = google_cloud_run_v2_service.layer5_reports.uri
}

output "reports_bucket" {
  description = "Cloud Storage bucket for PDF reports"
  value       = google_storage_bucket.reports.name
}

output "firestore_database" {
  description = "Firestore database name"
  value       = google_firestore_database.phantom.name
}

output "artifact_registry" {
  description = "Artifact Registry repository path"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/phantom-images"
}
