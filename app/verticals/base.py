"""
Universal Agent Economy OS - Vertical Credential Packs

This module provides the base definitions for vertical credential packs.
Vertical packs allow the OS to support standardized credential types
(e.g., Finance, Social, Cloud) with predefined scopes and descriptions.
"""
from typing import Dict, List
from pydantic import BaseModel

class CredentialDefinition(BaseModel):
    """
    Defines a standardized credential type within a vertical pack.
    """
    name: str
    description: str
    allowed_scopes: List[str]

class CredentialPack(BaseModel):
    """
    Defines a vertical credential pack containing multiple credential definitions.
    """
    pack_id: str
    name: str
    description: str
    credentials: Dict[str, CredentialDefinition]
