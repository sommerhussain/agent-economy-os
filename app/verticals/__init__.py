"""
Universal Agent Economy OS - Vertical Credential Packs Registry

This module automatically loads and exposes all vertical credential packs
for use by the Identity Engine. It supports dynamic validation of credential
types and scopes during rotation and proxy execution.
"""
import logging
from typing import Dict, Optional
from app.verticals.base import CredentialPack, CredentialDefinition
from app.verticals.finance import FinanceCredentialPack
from app.verticals.data import DataCredentialPack

logger = logging.getLogger(__name__)

# Registry of all loaded vertical packs
VERTICAL_PACKS: Dict[str, CredentialPack] = {
    FinanceCredentialPack.pack_id: FinanceCredentialPack,
    DataCredentialPack.pack_id: DataCredentialPack
}

def get_all_packs() -> Dict[str, CredentialPack]:
    """
    Returns all registered vertical credential packs.
    """
    return VERTICAL_PACKS

def get_credential_definition(credential_type: str) -> Optional[CredentialDefinition]:
    """
    Looks up a credential definition by its type across all loaded packs.
    Returns None if the credential type is not found in any pack.
    """
    for pack in VERTICAL_PACKS.values():
        if credential_type in pack.credentials:
            return pack.credentials[credential_type]
    return None
