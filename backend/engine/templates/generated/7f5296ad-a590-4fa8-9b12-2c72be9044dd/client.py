import httpx
import logging
from typing import Dict, Any, Optional

from models import PlaceOrderParams, ModifyOrderParams, CancelOrderParams

logger = logging.getLogger(__name__)

KITE_API_VERSION = "3"

class KiteConnectError(Exception):
    """Custom exception class for Kite Connect API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details

    def __str__(self):
        return f"KiteConnectError(status_code={self.status_code}, message='{self.message}', details={self.details})"

class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect v3 API."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade", timeout: float = 30.0):
        """
        Initializes the Kite Connect API client.

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
            "X-Kite-Version": KITE_API_VERSION,
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite uses form encoding
        }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout
        )
        logger.info(f"KiteConnectClient initialized for base URL: {self.base_url}")

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite Connect API."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Sending {method} request to {url} with data: {data}")

        try:
            response = await self.client.request(method, endpoint, data=data)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            json_response = response.json()
            logger.debug(f"Received successful response ({response.status_code}) from {url}: {json_response}")

            # Check for Kite specific error structure within a 2xx response (though usually errors are 4xx/5xx)
            if json_response.get("status") == "error":
                 error_type = json_response.get("error_type", "UnknownError")
                 message = json_response.get("message", "Unknown API error")
                 logger.error(f"Kite API returned error in success response: {error_type} - {message}")
                 raise KiteConnectError(message=message, status_code=response.status_code, details=json_response)

            return json_response

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                # Attempt to parse error details from Kite's JSON response
                error_data = e.response.json()
                message = error_data.get("message", f"HTTP Error {status_code}")
                error_type = error_data.get("error_type", "HTTPError")
                details = error_data
                logger.error(f"HTTP Error {status_code} from {url}: {error_type} - {message}. Details: {details}")
                raise KiteConnectError(message=message, status_code=status_code, details=details) from e
            except Exception:
                # Fallback if response is not JSON or parsing fails
                message = f"HTTP Error {status_code}: {e.response.text[:200]}" # Log snippet of response
                logger.error(f"HTTP Error {status_code} from {url}. Response: {e.response.text[:200]}")
                raise KiteConnectError(message=message, status_code=status_code) from e

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out for {method} {url}: {e}")
            raise KiteConnectError(message="Request timed out", details=str(e)) from e

        except httpx.RequestError as e:
            logger.error(f"Network or request error for {method} {url}: {e}")
            raise KiteConnectError(message="Network or request error", details=str(e)) from e

        except Exception as e:
            logger.exception(f"An unexpected error occurred during request to {url}: {e}")
            raise KiteConnectError(message="An unexpected client error occurred", details=str(e)) from e

    async def place_order(self, params: PlaceOrderParams) -> Dict[str, Any]:
        """Places an order."""
        endpoint = f"/orders/{params.variety}"
        # Convert model to dict, excluding None values, suitable for form encoding
        data = {k: v for k, v in params.dict().items() if v is not None and k != 'variety'}
        return await self._request("POST", endpoint, data=data)

    async def modify_order(self, params: ModifyOrderParams) -> Dict[str, Any]:
        """Modifies a pending order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        data = {k: v for k, v in params.dict().items() if v is not None and k not in ['variety', 'order_id']}
        return await self._request("PUT", endpoint, data=data)

    async def cancel_order(self, params: CancelOrderParams) -> Dict[str, Any]:
        """Cancels a pending order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # parent_order_id is sent as a query param in some older docs, but usually body param
        # Assuming body param based on typical REST patterns and lack of specific query param mention
        data = {k: v for k, v in params.dict().items() if v is not None and k not in ['variety', 'order_id']}
        return await self._request("DELETE", endpoint, data=data)

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("KiteConnectClient closed.")
