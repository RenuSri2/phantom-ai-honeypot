# =============================================================================
# PHANTOM — Terraform Variables
# =============================================================================

variable "project_id" {
  description = "Google Cloud project ID"
  type        = string
  default     = "phantom-hack2skill"
}

variable "region" {
  description = "Google Cloud region for all resources"
  type        = string
  default     = "us-central1"
}

variable "firestore_location" {
  description = "Firestore database location"
  type        = string
  default     = "nam5"
}

variable "cloud_run_hash" {
  description = "Cloud Run auto-generated hash suffix (used for service URLs)"
  type        = string
  default     = ""
}

variable "abuseipdb_api_key" {
  description = "AbuseIPDB API key for IP reputation lookups"
  type        = string
  sensitive   = true
  default     = ""
}
