-- Universal Agent Economy OS - Identity & Credential Schema
-- This schema establishes the foundational MCP/A2A-native identity engine.

-- Enable UUID extension for secure primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- Table: agents
-- Role: The core identity record for any autonomous agent in the economy.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast lookups by agent_id
CREATE INDEX IF NOT EXISTS idx_agents_agent_id ON public.agents(agent_id);

-- Basic RLS for agents (v0: Allow SELECT and INSERT)
ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow SELECT on agents" ON public.agents FOR SELECT USING (true);
CREATE POLICY "Allow INSERT on agents" ON public.agents FOR INSERT WITH CHECK (true);

-- ============================================================================
-- Table: credentials
-- Role: Secure vault for agent credentials, scoped for MCP/A2A operations.
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id TEXT NOT NULL REFERENCES public.agents(agent_id) ON DELETE CASCADE,
    credential_type TEXT NOT NULL,
    secret_data JSONB NOT NULL,
    expires_at TIMESTAMPTZ,
    scopes JSONB DEFAULT '[]'::jsonb,
    protocol_version TEXT DEFAULT 'mcp-a2a-v1',
    a2a_capabilities JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(agent_id, credential_type)
);

-- Indexes for fast credential lookups
CREATE INDEX IF NOT EXISTS idx_credentials_agent_id ON public.credentials(agent_id);
CREATE INDEX IF NOT EXISTS idx_credentials_type ON public.credentials(credential_type);

-- Basic RLS for credentials (v0: Allow SELECT and INSERT)
-- In production, SELECT should be restricted to the authenticated agent itself
ALTER TABLE public.credentials ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow SELECT on credentials" ON public.credentials FOR SELECT USING (true);
CREATE POLICY "Allow INSERT on credentials" ON public.credentials FOR INSERT WITH CHECK (true);
