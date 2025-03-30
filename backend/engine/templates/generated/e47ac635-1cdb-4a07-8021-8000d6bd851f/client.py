import httpx
import logging
from typing import Dict, Any, Optional
from models import PlaceOrderParams, ModifyOrderParams

logger = logging.getLogger(__name__)

# Define custom exceptions for Kite Connect specific errors
class KiteConnectError(Exception):
    """Base exception class for Kite Connect client errors."""
    def __init__(self, message="An error occurred with the Kite Connect API", code=500, error_type="APIError"):
        self.message = message
        self.code = code
        self.error_type = error_type
        super().__init__(f"[{error_type}/{code}] {message}")

class AuthenticationError(KiteConnectError):
    """Raised for authentication failures (403 Forbidden)."""
    def __init__(self, message="Authentication failed", error_type="TokenException"):
        super().__init__(message, code=403, error_type=error_type)

class NetworkError(KiteConnectError):
    """Raised for network-related issues."""
    def __init__(self, message="Network error connecting to Kite API"):
        super().__init__(message, code=503, error_type="NetworkException")

class TimeoutError(KiteConnectError):
    """Raised for request timeouts."""
    def __init__(self, message="Request timed out"):
        super().__init__(message, code=504, error_type="TimeoutException")

class OrderRejectionError(KiteConnectError):
    """Raised for specific order rejections (e.g., insufficient funds, validation)."""
    pass # Uses code/message/type from API response

class InputValidationError(KiteConnectError):
     """Raised for client-side or API-side input validation errors."""
     pass # Uses code/message/type from API response

class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect v3 API."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade", timeout: float = 30.0):
        """Initialize the Kite Connect client.

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
        self.timeout = timeout
        self.headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite uses form data
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout
        )
        # Note: Rate limiting (10 req/sec) is not actively enforced by this client.
        # Consider using a library like 'asyncio-throttle' or 'limits' for robust rate limiting.
        logger.info(f"KiteConnectClient initialized for base URL: {self.base_url}")

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite Connect API.

        Args:
            method: HTTP method (e.g., 'POST', 'PUT', 'GET', 'DELETE').
            endpoint: API endpoint path (e.g., '/orders/regular').
            data: Dictionary of form data for the request body (optional).

        Returns:
            The parsed JSON response from the API.

        Raises:
            AuthenticationError: If the API returns a 403 status.
            InputValidationError: If the API returns a 400 status.
            OrderRejectionError: For specific order-related errors (often 400).
            NetworkError: For connection errors.
            TimeoutError: If the request times out.
            KiteConnectError: For other API errors or unexpected statuses.
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Sending {method} request to {url} with data: {data}")
        try:
            response = await self.client.request(method, endpoint, data=data)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
            logger.debug(f"Received successful response ({response.status_code}) from {url}")
            return response.json()

        except httpx.TimeoutException as e:
            logger.error(f"Request timeout for {method} {url}: {e}")
            raise TimeoutError(f"Request timed out: {method} {url}") from e
        except httpx.NetworkError as e:
            logger.error(f"Network error for {method} {url}: {e}")
            raise NetworkError(f"Network error connecting to Kite API: {e}") from e
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                # Try to parse the error response body from Kite
                error_data = e.response.json()
                message = error_data.get("message", "Unknown API error")
                error_type = error_data.get("error_type", "APIException")
                logger.error(f"Kite API error ({status_code}) for {method} {url}: {error_type} - {message}")

                if status_code == 403:
                    raise AuthenticationError(message, error_type=error_type) from e
                elif status_code == 400:
                    # Distinguish between general validation and order rejection if possible
                    if "order" in message.lower() or "margin" in message.lower() or "funds" in message.lower():
                         raise OrderRejectionError(message, code=status_code, error_type=error_type) from e
                    else:
                         raise InputValidationError(message, code=status_code, error_type=error_type) from e
                else:
                    # General KiteConnectError for other 4xx/5xx
                    raise KiteConnectError(message, code=status_code, error_type=error_type) from e
            except Exception as parse_exc:
                # Fallback if response body is not JSON or parsing fails
                logger.error(f"HTTP error ({status_code}) for {method} {url} with non-JSON or unparseable body: {e.response.text}", exc_info=parse_exc)
                if status_code == 403:
                    raise AuthenticationError(f"Authentication failed (status {status_code})") from e
                else:
                    raise KiteConnectError(f"HTTP error {status_code}: {e.response.text}", code=status_code) from e
        except Exception as e:
            logger.error(f"Unexpected error during request to {method} {url}: {e}", exc_info=True)
            raise KiteConnectError(f"An unexpected error occurred: {e}") from e

    async def place_order_async(self, params: PlaceOrderParams) -> Dict[str, Any]:
        """Place an order asynchronously.

        Args:
            params: PlaceOrderParams object containing order details.

        Returns:
            Dictionary containing the API response (typically includes 'order_id').
        """
        endpoint = f"/orders/{params.variety}"
        # Convert Pydantic model to dict, excluding None values
        data = params.dict(exclude={'variety'}, exclude_none=True)
        # Ensure integer fields are sent as integers, float as floats
        for key, value in data.items():
            if isinstance(value, float):
                data[key] = str(value) # Kite API expects numbers as strings in form data sometimes
            elif isinstance(value, int):
                data[key] = str(value)

        logger.info(f"Placing {params.variety} order: {data}")
        return await self._request("POST", endpoint, data=data)

    async def modify_order_async(self, params: ModifyOrderParams) -> Dict[str, Any]:
        """Modify an existing order asynchronously.

        Args:
            params: ModifyOrderParams object containing modification details.

        Returns:
            Dictionary containing the API response (typically includes 'order_id').
        """
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Convert Pydantic model to dict, excluding None values and path params
        data = params.dict(exclude={'variety', 'order_id'}, exclude_none=True)
        # Ensure numeric fields are sent correctly
        for key, value in data.items():
             if isinstance(value, float):
                 data[key] = str(value)
             elif isinstance(value, int):
                 data[key] = str(value)

        logger.info(f"Modifying {params.variety} order {params.order_id}: {data}")
        return await self._request("PUT", endpoint, data=data)

    async def close(self):
        """Close the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("KiteConnectClient closed.")
