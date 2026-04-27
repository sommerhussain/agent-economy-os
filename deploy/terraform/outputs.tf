# Universal Agent Economy OS - Terraform Outputs
#
# These outputs provide acquirers and DevOps teams with the critical endpoints
# needed to integrate the Universal Agent Economy OS into their broader infrastructure.

output "proxy_endpoint" {
  description = "The public URL of the Universal Agent Economy OS proxy (e.g., ALB/API Gateway URL)"
  value       = "https://api.example.com" # Placeholder
}

output "redis_endpoint" {
  description = "Internal endpoint for the Redis caching and rate-limiting cluster"
  value       = "redis.internal.example.com:6379" # Placeholder
}

output "database_endpoint" {
  description = "Internal endpoint for the PostgreSQL / Supabase database"
  value       = "db.internal.example.com:5432" # Placeholder
  sensitive   = true
}

output "discovery_urls" {
  description = "URLs for the MCP and Agent discovery metadata, critical for A2A routing"
  value = {
    agent_card   = "https://api.example.com/.well-known/agent-card.json"
    mcp_manifest = "https://api.example.com/.well-known/mcp.json"
  }
}

output "dashboard_url" {
  description = "The public URL to access the /stats dashboard and pricing tiers"
  value       = "https://api.example.com/stats" # Placeholder
}
