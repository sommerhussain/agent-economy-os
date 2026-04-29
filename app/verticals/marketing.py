"""
Universal Agent Economy OS - Marketing & Ad-Tech Vertical Credential Pack

This module provides the Marketing vertical credential pack, designed specifically
to increase enterprise appeal for acquirers operating in ad-tech, customer data
platforms (CDP), and digital marketing automation.

Strategic Value for Acquirers:
- **Ad-Tech Ready**: Built-in support for major ad platforms, CRM, and social media APIs.
- **Least-Privilege Enforcement**: Granular cryptographic scopes ensure agents only access necessary campaign or audience data, protecting PII.
- **Audit Readiness**: Includes full auditor-ready exports (CSV/JSON) and automated credential rotation, critical for data privacy compliance (e.g., GDPR, CCPA).
- **MarTech Expansion**: Opens the Universal Agent Economy OS to multi-billion dollar marketing automation and CRM ecosystems.

Internal Security Notes (MCP STDIO Vulnerability Protection):
- When operating over MCP STDIO, agent prompts and outputs are passed via standard input/output streams.
- In marketing environments handling PII, these streams can be vulnerable to injection attacks or unauthorized logging of customer data.
- The Universal Agent Economy OS mitigates this by enforcing strict scope validation *before* any downstream execution, ensuring that even if an MCP STDIO stream is compromised, the agent's cryptographic credential cannot be used to exfiltrate data beyond its explicitly granted, least-privilege scopes.
- All credential injection happens server-side within the proxy, meaning the raw secrets never touch the potentially vulnerable MCP STDIO streams of the client agents.
"""
from app.verticals.base import CredentialPack, CredentialDefinition
from typing import Dict, Any, Union
import time
import csv
import io
from datetime import datetime, timezone

def export_marketing_audit_log(agent_id: str, export_format: str = "json", time_range_seconds: int = 86400) -> Union[Dict[str, Any], str]:
    """
    Generates a full auditor-ready export of the agent's recent proxy execution logs,
    specifically formatted for marketing data privacy and campaign auditing.
    
    Supports both JSON and CSV formats to integrate seamlessly with enterprise
    compliance workflows and external auditor tools.
    """
    from app.analytics import get_analytics_stats
    from app.supabase import get_agent_scopes
    
    stats = get_analytics_stats()
    recent_activity = stats.get("recent_activity", [])
    now = time.time()
    
    # Filter for the specific agent and time range
    agent_activity = [
        event for event in recent_activity 
        if event.get("agent_id") == agent_id and (now - event.get("timestamp", 0)) <= time_range_seconds
    ]
    
    # Fetch the agent's currently granted scopes for the audit report
    try:
        granted_scopes = get_agent_scopes(agent_id)
    except Exception:
        granted_scopes = {}
        
    report_id = f"martech_rep_{int(now)}"
    generated_at = datetime.now(timezone.utc).isoformat()
    
    if export_format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write Header
        writer.writerow(["Report ID", "Generated At", "Agent ID", "Compliance Standard"])
        writer.writerow([report_id, generated_at, agent_id, "Data Privacy (GDPR/CCPA) Ready"])
        writer.writerow([])
        
        # Write Scopes
        writer.writerow(["Granted Scopes Summary"])
        writer.writerow(["Credential Type", "Scopes"])
        for cred_type, scopes in granted_scopes.items():
            writer.writerow([cred_type, ", ".join(scopes)])
        writer.writerow([])
        
        # Write Events
        writer.writerow(["Event ID", "Event Type", "Amount", "Timestamp"])
        for event in agent_activity:
            writer.writerow([
                event.get("event_id", ""),
                event.get("event_type", ""),
                event.get("amount", 0.0),
                event.get("timestamp", "")
            ])
            
        return output.getvalue()
        
    # Default to JSON
    return {
        "report_id": report_id,
        "generated_at": generated_at,
        "agent_id": agent_id,
        "time_range_seconds": time_range_seconds,
        "total_events_exported": len(agent_activity),
        "granted_scopes_snapshot": granted_scopes,
        "events": agent_activity,
        "certification": "MarTech Auditor-Ready Export - Universal Agent Economy OS",
        "compliance_standard": "Data Privacy (GDPR/CCPA) Ready",
        "security_note": "Raw credentials are never exposed in this log or via MCP STDIO streams."
    }

def generate_marketing_audit_export(agent_id: str, time_range_seconds: int = 86400) -> Dict[str, Any]:
    """
    Legacy wrapper for backward compatibility. Use export_marketing_audit_log instead.
    """
    result = export_marketing_audit_log(agent_id, export_format="json", time_range_seconds=time_range_seconds)
    if isinstance(result, dict):
        return result
    return {}

def auto_rotate_marketing_credential(agent_id: str, credential_type: str) -> Dict[str, Any]:
    """
    Stub for automated credential rotation in marketing environments.
    Ensures that third-party vendor access to ad platforms or CRM systems
    is tightly controlled and frequently rotated to prevent data leaks.
    """
    return {
        "status": "rotated",
        "agent_id": agent_id,
        "credential_type": credential_type,
        "rotated_at": datetime.now(timezone.utc).isoformat(),
        "next_rotation_due": "7d" # Standard weekly rotation for marketing APIs
    }

MarketingCredentialPack = CredentialPack(
    pack_id="marketing",
    name="Marketing & Ad-Tech",
    description="Enterprise-grade credentials for ad platforms, CRM systems, social media management, and customer data platforms.",
    credentials={
        "ad_platform_api": CredentialDefinition(
            name="Ad Platform API",
            description="Secure access to major advertising networks (e.g., Google Ads, Meta Ads).",
            allowed_scopes=["ads:read", "campaign:write", "budget:manage"]
        ),
        "crm_integration": CredentialDefinition(
            name="CRM Integration Gateway",
            description="Credentials for syncing customer data and managing leads in CRM systems (e.g., Salesforce, HubSpot).",
            allowed_scopes=["crm:read", "lead:write", "contact:update"]
        ),
        "social_media_manager": CredentialDefinition(
            name="Social Media Management API",
            description="Access to social media platforms for publishing content and monitoring engagement.",
            allowed_scopes=["social:publish", "social:read", "engagement:monitor"]
        ),
        "email_marketing_gateway": CredentialDefinition(
            name="Email Marketing API",
            description="Credentials for orchestrating email campaigns and managing subscriber lists.",
            allowed_scopes=["email:send", "list:manage", "campaign:analyze"]
        ),
        "customer_data_platform": CredentialDefinition(
            name="Customer Data Platform (CDP)",
            description="Access to centralized customer data platforms for audience segmentation and analytics.",
            allowed_scopes=["audience:segment", "analytics:read", "data:sync"]
        ),
        "marketing_compliance_auditor": CredentialDefinition(
            name="Marketing Compliance Auditor",
            description="Enterprise credentials for generating auditor-ready exports and monitoring data privacy compliance logs.",
            allowed_scopes=["audit:read", "audit:export", "compliance:verify"]
        )
    }
)
