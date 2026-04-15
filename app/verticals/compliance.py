from app.verticals.base import CredentialPack, CredentialDefinition

ComplianceCredentialPack = CredentialPack(
    pack_id="compliance",
    name="Compliance & Governance",
    description="Enterprise-grade credentials for audit logging, KYC, regulatory reporting, and smart contract audits.",
    credentials={
        "audit_log_access": CredentialDefinition(
            name="Audit Log Access",
            description="Read-only access to immutable transaction and proxy execution audit logs.",
            allowed_scopes=["audit:read", "audit:export"]
        ),
        "kyc_verification": CredentialDefinition(
            name="KYC Verification Provider",
            description="Credentials for third-party Know Your Customer (KYC) and AML verification services.",
            allowed_scopes=["kyc:verify", "identity:verify"]
        ),
        "regulatory_reporting": CredentialDefinition(
            name="Regulatory Reporting API",
            description="Access to automated tax and regulatory reporting endpoints.",
            allowed_scopes=["report:generate", "report:submit"]
        ),
        "smart_contract_audit": CredentialDefinition(
            name="Smart Contract Auditor",
            description="Access to automated smart contract vulnerability scanning and formal verification tools.",
            allowed_scopes=["contract:scan", "contract:verify"]
        ),
        "gdpr_compliance": CredentialDefinition(
            name="GDPR Data Controller",
            description="Credentials for managing data subject access requests and right-to-be-forgotten operations.",
            allowed_scopes=["data:delete", "data:export", "consent:manage"]
        )
    }
)
