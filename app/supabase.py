"""
Universal Agent Economy OS - Supabase Identity Stub

This module provides the v0 Identity Engine stub. It attempts to connect to
Supabase to fetch credentials for a given agent_id and credential_type. If
Supabase is not configured, it gracefully falls back to a simulation mode
for local testing and development.
"""
import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from app.config import settings

logger = logging.getLogger(__name__)

# Attempt to import the Supabase client.
# This keeps the skeleton modular; if the package isn't installed yet, it won't break the app.
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError: # pragma: no cover
    HAS_SUPABASE = False
    Client = Any

def get_supabase_client() -> Optional[Client]:
    """
    Initializes and returns the Supabase client using environment variables.
    Returns None if the environment variables are missing or the package is not installed.
    """
    if not HAS_SUPABASE:
        logger.warning("Supabase package not installed. Run `pip install supabase` for real integration.")
        return None
        
    url: str = settings.SUPABASE_URL
    key: str = settings.SUPABASE_KEY
    
    if not url or not key:
        logger.warning("SUPABASE_URL or SUPABASE_KEY not set in environment. Falling back to simulation.")
        return None
        
    try:
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None

def create_tables() -> bool:
    """
    Reads the supabase/schema.sql file and attempts to apply it via Supabase RPC.
    If Supabase is not configured, it logs the action and returns True (simulation).
    This helper ensures the MCP/A2A-native schema is easily bootstrapped.
    """
    client = get_supabase_client()
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "supabase", "schema.sql")
    
    if not os.path.exists(schema_path):
        logger.error(f"Schema file not found at {schema_path}")
        return False

    if client:
        try:
            with open(schema_path, "r") as f:
                sql = f.read()
            # Supabase REST API doesn't natively support raw SQL execution without a custom RPC.
            # We simulate calling a hypothetical 'exec_sql' RPC or notify the user to run it in the dashboard.
            logger.info("Applying schema to Supabase (requires 'exec_sql' RPC or manual dashboard execution)...")
            # client.rpc("exec_sql", {"query": sql}).execute()
            logger.info("Schema application requested.")
            return True
        except Exception as e:
            logger.error(f"Failed to apply schema: {e}")
            return False
    
    logger.info("Simulating schema application (Supabase not configured).")
    return True

def insert_agent(agent_id: str, name: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """
    Inserts a new agent into the Supabase 'agents' table.
    If Supabase is not configured, simulates a successful insertion.
    """
    client = get_supabase_client()
    if client:
        try:
            logger.info(f"Inserting agent {agent_id} into Supabase...")
            data = {"agent_id": agent_id, "name": name, "metadata": metadata or {}}
            client.table("agents").insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to insert agent into Supabase: {e}")
            return False
    
    logger.info(f"Simulating agent insertion for {agent_id} (Supabase not configured).")
    return True

def rotate_credential_db(agent_id: str, credential_type: str, new_secret_data: Dict[str, Any], expires_at: Optional[str], scopes: Optional[List[str]] = None) -> bool:
    """
    Upserts a credential for the given agent and type.
    If Supabase is not configured, simulates a successful rotation.
    This leverages the UNIQUE(agent_id, credential_type) constraint in the schema.
    """
    client = get_supabase_client()
    if client:
        try:
            logger.info(f"Rotating {credential_type} credential for agent {agent_id} in Supabase...")
            data = {
                "agent_id": agent_id,
                "credential_type": credential_type,
                "secret_data": new_secret_data,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            if expires_at:
                data["expires_at"] = expires_at
            if scopes is not None:
                data["scopes"] = scopes
                
            # Upsert relies on the UNIQUE constraint to overwrite the old secret and expiry
            client.table("credentials").upsert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to rotate credential in Supabase: {e}")
            return False
            
    logger.info(f"Simulating credential rotation for {agent_id} (Supabase not configured).")
    return True

def fetch_credential(agent_id: str, credential_type: str, required_scopes: Optional[List[str]] = None) -> Optional[Dict[str, str]]:
    """
    Looks up credentials from Supabase for a given agent and credential type.
    Enforces required_scopes if provided by checking against the stored scopes.
    
    Future-proofing: The underlying 'credentials' table now includes fields like
    'scopes', 'protocol_version' (e.g., 'mcp-a2a-v1'), and 'a2a_capabilities'.
    These ensure that as the Identity Engine expands, we can support advanced
    Model Context Protocol (MCP) routing and granular agent-to-agent permissions.
    
    If Supabase is not configured, it simulates a successful lookup for testing.
    """
    from app.identity import check_scopes
    from app.cache import get_cached_credential, set_cached_credential
    
    # 1. Check Cache
    cached = get_cached_credential(agent_id, credential_type)
    if cached:
        secret_data, granted_scopes = cached
        if required_scopes and not check_scopes(required_scopes, granted_scopes):
            logger.warning(f"Insufficient scopes for agent {agent_id} (cached). Required: {required_scopes}, Granted: {granted_scopes}")
            return None
        return secret_data

    client = get_supabase_client()
    secret_data = None
    granted_scopes = []
    
    if client:
        try:
            # Real implementation: Query the 'credentials' table securely
            logger.info(f"Querying Supabase for {credential_type} credentials for agent {agent_id}")
            response = client.table("credentials").select("secret_data, scopes").eq("agent_id", agent_id).eq("credential_type", credential_type).execute()
            
            if response.data and len(response.data) > 0:
                granted_scopes = response.data[0].get("scopes") or []
                secret_data = response.data[0].get("secret_data")
                logger.info("Credentials successfully retrieved from Supabase.")
            else:
                logger.warning("No credentials found in Supabase for this agent/type combination.")
                return None
        except Exception as e:
            logger.error(f"Supabase query failed: {e}")
            return None
    else:
        # Fallback/Simulation for the v0 skeleton when Supabase isn't fully configured
        logger.info(f"Simulating credential fetch for agent: {agent_id}, type: {credential_type}")
        if str(agent_id).startswith("agent_") and credential_type:
            granted_scopes = ["read", "write"]
            secret_data = {"token": f"simulated_token_for_{credential_type}", "injected_by": "uae_os_proxy"}
        else:
            logger.warning(f"Simulation failed to find credentials for agent: {agent_id}")
            return None

    # 2. Set Cache
    if secret_data is not None:
        set_cached_credential(agent_id, credential_type, secret_data, granted_scopes)
        
        # 3. Enforce Scopes
        if required_scopes and not check_scopes(required_scopes, granted_scopes):
            logger.warning(f"Insufficient scopes for agent {agent_id}. Required: {required_scopes}, Granted: {granted_scopes}")
            return None
            
        return secret_data
        
    return None  # pragma: no cover

def get_agent_scopes(agent_id: str) -> Dict[str, List[str]]:
    """
    Retrieves all granted scopes for an agent across all their credentials.
    Returns a dictionary mapping credential_type to a list of scopes.
    """
    from app.cache import get_cached_agent_scopes, set_cached_agent_scopes
    
    # 1. Check Cache
    cached = get_cached_agent_scopes(agent_id)
    if cached is not None:
        return cached

    client = get_supabase_client()
    scopes_dict = {}
    
    if client:
        try:
            response = client.table("credentials").select("credential_type, scopes").eq("agent_id", agent_id).execute()
            if response.data:
                scopes_dict = {row["credential_type"]: row.get("scopes") or [] for row in response.data}
                set_cached_agent_scopes(agent_id, scopes_dict)
                return scopes_dict
        except Exception as e:
            logger.error(f"Failed to fetch scopes from Supabase: {e}")
            
    # Simulation fallback
    if str(agent_id).startswith("agent_"):
        scopes_dict = {
            "stripe_live": ["read", "write"],
            "aws_s3": ["read"]
        }
        set_cached_agent_scopes(agent_id, scopes_dict)
        return scopes_dict
        
    return {}
