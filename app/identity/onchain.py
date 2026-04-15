from app.verticals.base import CredentialPack, CredentialDefinition

class OnChainIdentityStub:
    """
    Stub for ERC-8004 on-chain identity and credentials.
    Future-proofs the Identity Engine for hybrid fiat/on-chain credentials.
    """
    
    @staticmethod
    def get_credential_pack() -> CredentialPack:
        return CredentialPack(
            pack_id="onchain",
            name="On-Chain Identity (ERC-8004)",
            description="Core credentials for on-chain identity, wallets, and smart contract interactions.",
            credentials={
                "erc8004_identity": CredentialDefinition(
                    name="ERC-8004 Identity",
                    description="On-chain identity profile and attestations.",
                    allowed_scopes=["wallet:read", "nft:verify", "ens:resolve"]
                ),
                "wallet_connect": CredentialDefinition(
                    name="WalletConnect Session",
                    description="Active WalletConnect session for signing transactions.",
                    allowed_scopes=["wallet:read", "tx:sign"]
                ),
                "siwe_session": CredentialDefinition(
                    name="Sign-In with Ethereum (SIWE)",
                    description="Authenticated session via EIP-4361 for off-chain services.",
                    allowed_scopes=["auth:siwe", "session:read"]
                ),
                "verifiable_credential": CredentialDefinition(
                    name="W3C Verifiable Credential",
                    description="On-chain verifiable credential for hybrid identity proofs.",
                    allowed_scopes=["vc:read", "vc:verify", "vc:issue"]
                )
            }
        )

OnChainCredentialPack = OnChainIdentityStub.get_credential_pack()
