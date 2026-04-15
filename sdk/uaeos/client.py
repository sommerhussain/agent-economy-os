"""
Universal Agent Economy OS - Python SDK Client

This module contains the primary UAEOSClient class for interacting with the
core proxy, identity engine, and billing systems. It provides robust error
handling, automatic retries for transient failures, and full async support.
"""
import httpx
import asyncio
import logging
from typing import Any, Dict, Optional, List, Type, TypeVar

logger = logging.getLogger(__name__)

class UAEError(Exception):
    """Base exception for all UAE OS SDK errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, error_code: Optional[str] = None, request_id: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.request_id = request_id
        super().__init__(f"[{error_code or 'UNKNOWN'}] {message} (HTTP {status_code}, ReqID: {request_id})")

class AuthError(UAEError):
    """Raised when authentication fails (401)."""
    pass

class RateLimitError(UAEError):
    """Raised when the agent exceeds their rate limit (429)."""
    def __init__(self, message: str, retry_after: int, request_id: Optional[str] = None):
        self.retry_after = retry_after
        super().__init__(message, status_code=429, error_code="RATE_LIMIT_EXCEEDED", request_id=request_id)

class InsufficientScopesError(UAEError):
    """Raised when an agent lacks required scopes (403)."""
    pass

class APIError(UAEError):
    """Raised for general API errors (4xx, 5xx)."""
    pass


class UAEOSClient:
    """
    Asynchronous Python client for the Universal Agent Economy OS.
    
    Provides robust connection pooling, automatic retries for transient errors,
    and structured exception handling.
    
    Example:
        ```python
        async with UAEOSClient(api_key="sk_test_...") as client:
            try:
                response = await client.execute(
                    agent_id="agent_1",
                    tool_call={"url": "https://api.example.com", "action": "read"},
                    credential_type="stripe_live",
                    payment_amount=0.05
                )
                print(response)
            except RateLimitError as e:
                print(f"Rate limited. Retry after {e.retry_after}s")
        ```
    """
    def __init__(self, api_key: str, base_url: str = "http://127.0.0.1:8000", max_retries: int = 3):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "UAEOSClient":
        self._client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def close(self) -> None:
        """Manually close the underlying HTTP client if not using async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            # Fallback for users not using async with
            self._client = httpx.AsyncClient(base_url=self.base_url, headers=self.headers)
        return self._client

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Parses the structured error response and raises the appropriate Python exception."""
        try:
            data = response.json()
            message = data.get("message", data.get("detail", "Unknown error occurred"))
            error_code = data.get("error_code")
            request_id = data.get("request_id")
        except Exception:
            message = response.text
            error_code = None
            request_id = response.headers.get("X-Request-ID")

        if response.status_code == 401:
            raise AuthError(message, status_code=401, error_code=error_code, request_id=request_id)
        elif response.status_code == 403:
            raise InsufficientScopesError(message, status_code=403, error_code=error_code, request_id=request_id)
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 1))
            raise RateLimitError(message, retry_after=retry_after, request_id=request_id)
        else:
            raise APIError(message, status_code=response.status_code, error_code=error_code, request_id=request_id)

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Internal helper for making HTTP requests with exponential backoff retries
        for transient failures (429, 5xx).
        """
        client = self._get_client()
        retries = 0
        backoff = 1.0

        while True:
            try:
                response = await client.request(method, endpoint, **kwargs)
                
                if response.is_success:
                    return response.json()
                    
                # Handle 429 Rate Limit specifically for retries
                if response.status_code == 429 and retries < self.max_retries:
                    retry_after = int(response.headers.get("Retry-After", backoff))
                    logger.warning(f"Rate limited. Retrying in {retry_after}s...")
                    await asyncio.sleep(retry_after)
                    retries += 1
                    continue
                    
                # Handle 5xx Server Errors for retries
                if response.status_code >= 500 and retries < self.max_retries:
                    logger.warning(f"Server error {response.status_code}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    retries += 1
                    backoff *= 2
                    continue
                    
                # If we reach here, it's a non-retriable error or we exhausted retries
                self._handle_error_response(response)

            except httpx.RequestError as e:
                if retries < self.max_retries:
                    logger.warning(f"Connection error: {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    retries += 1
                    backoff *= 2
                    continue
                raise APIError(f"Network error: {str(e)}")

    async def register_agent(self, agent_id: str, name: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Registers a new autonomous agent in the Identity Engine.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name for the agent
            metadata: Optional JSON metadata
            
        Returns:
            Dict containing registration success and agent details.
        """
        payload = {
            "agent_id": agent_id,
            "name": name,
            "metadata": metadata or {}
        }
        return await self._request("POST", "/agents/register", json=payload)

    async def rotate_credential(self, agent_id: str, credential_type: str, new_secret_data: Dict[str, Any], expires_in_days: Optional[float] = None) -> Dict[str, Any]:
        """
        Rotates or issues a new credential for an autonomous agent.
        
        Args:
            agent_id: The agent's unique ID
            credential_type: The type of credential (e.g., 'stripe_live')
            new_secret_data: The actual secret data to securely store
            expires_in_days: Optional time-to-live in days
            
        Returns:
            Dict containing success status and expiry timestamp.
        """
        payload = {
            "agent_id": agent_id,
            "credential_type": credential_type,
            "new_secret_data": new_secret_data
        }
        if expires_in_days is not None:
            payload["expires_in_days"] = expires_in_days
            
        return await self._request("POST", "/credentials/rotate", json=payload)

    async def execute(self, agent_id: str, tool_call: Dict[str, Any], credential_type: str, payment_amount: Optional[float] = None, payment_proof: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes a tool call through the secure proxy, handling credential injection and x402 settlement.
        
        Args:
            agent_id: The calling agent's ID
            tool_call: The payload defining the tool execution (url, method, etc.)
            credential_type: The required credential type to inject
            payment_amount: Optional x402 micropayment amount to settle
            payment_proof: Optional transaction ID from a previous settlement to retry without double charging
            
        Returns:
            Dict containing execution success, settlement status, and audit ID.
        """
        payload = {
            "agent_id": agent_id,
            "tool_call": tool_call,
            "credential_type": credential_type
        }
        if payment_amount is not None:
            payload["payment_amount"] = payment_amount
        if payment_proof is not None:
            payload["payment_proof"] = payment_proof
            
        return await self._request("POST", "/proxy/execute", json=payload)

    async def execute_payment(self, agent_id: str, payment_amount: float, target_agent_id: str, action: str = "payment") -> Dict[str, Any]:
        """
        Executes a direct A2A payment without a downstream HTTP call.
        This uses the A2A routing stub combined with the settlement engine.
        
        Args:
            agent_id: The calling agent's ID
            payment_amount: The x402 micropayment amount to settle
            target_agent_id: The destination agent ID
            action: Optional action description
            
        Returns:
            Dict containing execution success, settlement status, and audit ID.
        """
        tool_call = {
            "target_agent_id": target_agent_id,
            "action": action
        }
        return await self.execute(
            agent_id=agent_id,
            tool_call=tool_call,
            credential_type="stripe_live", # Default to live payment credential
            payment_amount=payment_amount
        )

    async def get_scopes(self, agent_id: str) -> Dict[str, Any]:
        """
        Retrieves all granted scopes for an agent across all their credentials.
        """
        return await self._request("GET", f"/agents/{agent_id}/scopes")

    async def get_invoice(self, agent_id: str) -> Dict[str, Any]:
        """
        Generates a usage-based invoice stub for the specified agent.
        """
        return await self._request("GET", f"/billing/invoice/{agent_id}")

    async def get_stats(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves global usage statistics and recent invoices from the dashboard.
        If agent_id is provided, also returns the usage vs limits for that agent.
        """
        endpoint = "/stats"
        if agent_id:
            endpoint += f"?agent_id={agent_id}"
        return await self._request("GET", endpoint)

    async def get_vertical_packs(self) -> Dict[str, Any]:
        """
        Retrieves all registered vertical credential packs and their definitions.
        """
        return await self._request("GET", "/verticals")

    async def discover_premium_tools(self, agent_id: str, payment_amount: float = 0.01) -> Dict[str, Any]:
        """
        Executes a paid discovery call to find premium tools and capabilities available on the network.
        
        Args:
            agent_id: The calling agent's ID
            payment_amount: The x402 micropayment amount to settle for discovery (default 0.01)
            
        Returns:
            Dict containing the discovery data with premium tools.
        """
        tool_call = {
            "action": "discover",
            "required_payment": payment_amount
        }
        return await self.execute(
            agent_id=agent_id,
            tool_call=tool_call,
            credential_type="stripe_live", # Default to live payment credential
            payment_amount=payment_amount
        )
