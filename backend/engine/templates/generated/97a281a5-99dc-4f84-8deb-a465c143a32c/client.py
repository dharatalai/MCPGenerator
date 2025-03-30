import httpx
import logging
import os
import asyncio
from typing import Dict, Any, Optional
from models import PlaceOrderParams, ModifyOrderParams, CancelOrderParams

logger = logging.getLogger(__name__)

# Define Kite Connect API specific exceptions
class KiteApiException(Exception):
    """Custom exception for Kite Connect API errors."""
    def __init__(self, message, code=None, status_code=None):
        self.message = message
        self.code = code  # Kite specific error code (if available)
        self.status_code = status_code # HTTP status code
        super().__init__(self.message)

    def __str__(self):
        return f"KiteApiException: {self.message} (Code: {self.code}, HTTP Status: {self.status_code})"

class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect Orders API."""

    DEFAULT_BASE_URL = "https://api.kite.trade"
    KITE_API_VERSION = "3" # Specify the Kite API version
    # Basic rate limiting: delay between requests (in seconds)
    # A more robust solution would use token buckets or similar.
    REQUEST_DELAY = 0.1 # Corresponds to ~10 requests/sec limit

    def __init__(self, api_key: str, access_token: str, base_url: Optional[str] = None, timeout: float = 30.0):
        """
        Initializes the Kite Connect client.

        Args:
            api_key: Your Kite Connect API key.
            access_token: The access token obtained after login.
            base_url: The base URL for the Kite API. Defaults to production URL.
            timeout: Default request timeout in seconds.
        """
        if not api_key or not access_token:
            raise ValueError("API key and access token are required.")

        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.timeout = timeout

        self.headers = {
            "X-Kite-Version": self.KITE_API_VERSION,
            "Authorization": f"token {self.api_key}:{self.access_token}",
            # Kite API expects form-encoded data, not JSON
            # 'Content-Type': 'application/x-www-form-urlencoded' # httpx sets this automatically for `data=`
        }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout
        )

        self._last_request_time = 0

    async def _rate_limit_delay(self):
        """Applies a simple delay to respect rate limits."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self.REQUEST_DELAY:
            await asyncio.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Internal method to make API requests.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint path (e.g., '/orders/regular').
            data: Dictionary of data to send (will be form-encoded for POST/PUT).

        Returns:
            The JSON response data as a dictionary.

        Raises:
            KiteApiException: If the API returns an error or the request fails.
        """
        await self._rate_limit_delay()
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making request: {method} {url} Data: {data}")

        try:
            response = await self.client.request(method, url, data=data)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
            response_data = response.json()

            # Kite API typically wraps successful responses in a 'data' field
            if isinstance(response_data, dict) and 'status' in response_data:
                if response_data['status'] == 'success':
                    return response_data.get('data', {}) # Return the content within 'data'
                elif response_data['status'] == 'error':
                    error_message = response_data.get('message', 'Unknown API error')
                    error_type = response_data.get('error_type', None) # e.g., InputException, TokenException
                    logger.error(f"Kite API Error: {error_message} (Type: {error_type})")
                    raise KiteApiException(message=error_message, code=error_type, status_code=response.status_code)
                else:
                    # Unexpected status value
                    logger.error(f"Unexpected status in Kite API response: {response_data.get('status')}")
                    raise KiteApiException(message="Unexpected status in API response", status_code=response.status_code)
            else:
                # Handle cases where response might not follow the {status: ..., data: ...} structure
                # This might happen for certain errors or unexpected responses.
                logger.warning(f"Unexpected API response format: {response_data}")
                # Attempt to return data if it looks valid, otherwise raise error
                if isinstance(response_data, dict):
                    return response_data # Assume it's the data if no status field
                else:
                    raise KiteApiException(message="Received non-dictionary response", status_code=response.status_code)

        except httpx.HTTPStatusError as e:
            # Handle HTTP errors (4xx, 5xx)
            try:
                # Try to parse error details from response body
                error_data = e.response.json()
                message = error_data.get('message', f"HTTP Error: {e.response.status_code}")
                code = error_data.get('error_type', None)
            except Exception:
                message = f"HTTP Error: {e.response.status_code} - {e.response.text[:100]}" # Truncate long responses
                code = None
            logger.error(f"HTTP Error during API request to {e.request.url}: {message}", exc_info=False)
            raise KiteApiException(message=message, code=code, status_code=e.response.status_code) from e

        except httpx.RequestError as e:
            # Handle network errors, timeouts, etc.
            logger.error(f"Request failed for {e.request.url}: {e}", exc_info=True)
            raise KiteApiException(message=f"Network request failed: {e}", status_code=None) from e

        except Exception as e:
            # Catch any other unexpected errors during request/processing
            logger.exception(f"An unexpected error occurred during API request to {url}")
            raise KiteApiException(message=f"An unexpected error occurred: {str(e)}", status_code=None) from e

    async def place_order(self, params: PlaceOrderParams) -> Dict[str, str]:
        """
        Places an order.

        Args:
            params: PlaceOrderParams object containing order details.

        Returns:
            Dictionary containing the 'order_id'.
        """
        endpoint = f"/orders/{params.variety}"
        # Convert Pydantic model to dict, excluding None values
        payload = params.dict(exclude_none=True, exclude={'variety'}) # Variety is in the path
        # Kite API expects integer quantities
        if 'quantity' in payload: payload['quantity'] = int(payload['quantity'])
        if 'disclosed_quantity' in payload: payload['disclosed_quantity'] = int(payload['disclosed_quantity'])
        if 'iceberg_legs' in payload: payload['iceberg_legs'] = int(payload['iceberg_legs'])
        if 'iceberg_quantity' in payload: payload['iceberg_quantity'] = int(payload['iceberg_quantity'])

        # Convert float prices to strings if needed by API (check Kite docs, usually not needed for form data)
        # if 'price' in payload: payload['price'] = str(payload['price'])
        # if 'trigger_price' in payload: payload['trigger_price'] = str(payload['trigger_price'])

        logger.info(f"Placing order: POST {endpoint}, Payload: {payload}")
        return await self._request("POST", endpoint, data=payload)

    async def modify_order(self, params: ModifyOrderParams) -> Dict[str, str]:
        """
        Modifies a pending order.

        Args:
            params: ModifyOrderParams object containing modification details.

        Returns:
            Dictionary containing the 'order_id'.
        """
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        payload = params.dict(exclude_none=True, exclude={'variety', 'order_id'}) # Path params excluded

        if 'quantity' in payload: payload['quantity'] = int(payload['quantity'])
        if 'disclosed_quantity' in payload: payload['disclosed_quantity'] = int(payload['disclosed_quantity'])

        logger.info(f"Modifying order: PUT {endpoint}, Payload: {payload}")
        return await self._request("PUT", endpoint, data=payload)

    async def cancel_order(self, params: CancelOrderParams) -> Dict[str, str]:
        """
        Cancels a pending order.

        Args:
            params: CancelOrderParams object containing order details.

        Returns:
            Dictionary containing the 'order_id'.
        """
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # No payload needed for DELETE
        logger.info(f"Cancelling order: DELETE {endpoint}")
        return await self._request("DELETE", endpoint)

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("Kite Connect client closed.")
