# Universal Agent Economy OS - Terraform Variables
#
# This file defines the core configuration variables required for a one-command deployment.
# These map directly to the environment variables defined in app/config.py and railway.toml.

variable "environment" {
  description = "Deployment environment (e.g., dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Name of the application"
  type        = string
  default     = "agent-economy-os"
}

# ==========================================
# Core Secrets (To be injected via CI/CD or Secret Manager, aligning with app/config.py)
# ==========================================

variable "api_key" {
  description = "Master API key for proxy authentication (API_KEY)"
  type        = string
  sensitive   = true
}

variable "stripe_secret_key" {
  description = "Stripe secret key for x402 settlement engine (STRIPE_SECRET_KEY)"
  type        = string
  sensitive   = true
}

variable "stripe_webhook_secret" {
  description = "Stripe webhook secret for secure payment confirmation (STRIPE_WEBHOOK_SECRET)"
  type        = string
  sensitive   = true
}

variable "supabase_url" {
  description = "Supabase project URL for the Identity Engine (SUPABASE_URL)"
  type        = string
}

variable "supabase_key" {
  description = "Supabase service role key (SUPABASE_KEY)"
  type        = string
  sensitive   = true
}

variable "redis_url" {
  description = "Redis connection string (REDIS_URL)"
  type        = string
  sensitive   = true
}
