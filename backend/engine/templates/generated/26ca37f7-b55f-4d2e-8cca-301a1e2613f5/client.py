import logging
from typing import Any, Dict, Optional

import httpx

from models import CancelOrderParams, ModifyOrderParams, PlaceOrderParams

logger = logging.getLogger(__name__)

KITE_API_VERSION = "3" # As per Kite Connect v3 documentation

class KiteConnectError(Exception):
    """Custom exception class for Kite Connect API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details if details else {}

    def __str__(self):
        return f"KiteConnectError(status_code={self.status_code}): {super().__str__()}"

class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect API v3 (Orders)."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade", timeout: float = 30.0):
        """
        Initializes the Kite Connect client.

        Args:
            api_key: Your Kite Connect API key.
            access_token: The access token obtained after successful login.
            base_url: The base URL for the Kite Connect API.
            timeout: Default request timeout in seconds.
        """
        if not api_key or not access_token:
            raise ValueError("API key and access token are required.")

        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url
        self._headers = {
            "X-Kite-Version": KITE_API_VERSION,
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite API uses form encoding
        }
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=timeout
        )
        # Note: Rate limiting (10 requests/sec) is enforced by Kite. This client
        # does not implement explicit rate limiting. Ensure usage stays within limits.
        logger.info(f"KiteConnectClient initialized for base URL: {self.base_url}")
        logger.warning("Ensure API usage adheres to Kite Connect rate limits (e.g., 10 requests/second).")

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite API."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making Kite API request: {method} {url}")
        logger.debug(f"Request Headers: {self._headers}") # Be cautious logging tokens in production
        logger.debug(f"Request Params: {params}")
        logger.debug(f"Request Data: {data}")

        try:
            response = await self._client.request(method, endpoint, params=params, data=data)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses
            response_data = response.json()
            logger.debug(f"Kite API Response Status: {response.status_code}")
            logger.debug(f"Kite API Response Body: {response_data}")

            # Check for Kite specific error structure within a 200 OK response
            if isinstance(response_data, dict) and response_data.get('status') == 'error':
                logger.error(f"Kite API returned error in success response: {response_data}")
                raise KiteConnectError(
                    message=response_data.get('message', 'Unknown API error'),
                    status_code=response.status_code,
                    details=response_data
                )

            return response_data

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                # Attempt to parse error details from response body
                error_data = e.response.json()
                message = error_data.get('message', f"HTTP Error {status_code}")
                details = error_data
                logger.error(f"Kite API HTTP Error {status_code}: {message} | Details: {details}")
            except Exception:
                # Fallback if response body is not JSON or parsing fails
                message = f"HTTP Error {status_code}: {e.response.text or 'No details available'}"
                details = {"raw_response": e.response.text}
                logger.error(f"Kite API HTTP Error {status_code}: {message}")

            # Map specific status codes if needed (e.g., 401/403 for auth)
            if status_code in [401, 403]:
                raise KiteConnectError("AuthenticationError: Invalid API key or access token.", status_code, details)
            elif status_code == 404:
                 raise KiteConnectError("NotFoundError: Resource not found.", status_code, details)
            elif status_code == 400:
                 raise KiteConnectError("InvalidInputError: Bad request, check parameters.", status_code, details)
            elif status_code == 429:
                 raise KiteConnectError("RateLimitError: Too many requests.", status_code, details)
            else:
                raise KiteConnectError(message, status_code, details)

        except httpx.TimeoutException as e:
            logger.error(f"Kite API request timed out: {e}")
            raise KiteConnectError("NetworkError: Request timed out.")
        except httpx.RequestError as e:
            logger.error(f"Kite API request failed: {e}")
            raise KiteConnectError(f"NetworkError: Could not connect to Kite API. {e}")
        except Exception as e:
            logger.exception("An unexpected error occurred during Kite API request")
            raise KiteConnectError(f"Unexpected error: {str(e)}")

    async def place_order_async(self, params: PlaceOrderParams) -> Dict[str, Any]:
        """Place an order asynchronously."""
        endpoint = f"/orders/{params.variety}"
        # Convert model to dict, excluding None values and the 'variety' path param
        data = params.dict(exclude={'variety'}, exclude_unset=True)
        # Convert boolean/numeric types to strings if required by API (Kite uses form encoding, usually handles this)
        # Ensure required fields based on logic (e.g., price for LIMIT) are present (handled by Pydantic model)
        return await self._request("POST", endpoint, data=data)

    async def modify_order_async(self, params: ModifyOrderParams) -> Dict[str, Any]:
        """Modify an order asynchronously."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Convert model to dict, excluding None values and path params
        data = params.dict(exclude={'variety', 'order_id'}, exclude_unset=True)
        return await self._request("PUT", endpoint, data=data)

    async def cancel_order_async(self, params: CancelOrderParams) -> Dict[str, Any]:
        """Cancel an order asynchronously."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # No data payload for DELETE usually, params are in the URL
        return await self._request("DELETE", endpoint)

    async def close(self):
        """Closes the underlying HTTP client."""
        await self._client.aclose()
        logger.info("KiteConnectClient closed.")
