import asyncio
import logging
from typing import Any, Dict, Optional

import httpx
from pydantic import ValidationError

from models import (
    CancelOrderParams,
    ModifyRegularOrderParams,
    PlaceOrderParams,
)

logger = logging.getLogger(__name__)

# Define custom exceptions
class KiteConnectAPIError(Exception):
    """Represents an error returned by the Kite Connect API."""

    def __init__(self, message: str, code: Optional[int] = None):
        self.message = message
        self.code = code
        super().__init__(f"[{code}] {message}" if code else message)


class ZerodhaKiteConnectClient:
    """Asynchronous client for interacting with the Zerodha Kite Connect v3 Orders API."""

    DEFAULT_TIMEOUT = 30.0  # seconds
    KITE_API_VERSION = "3"

    def __init__(
        self,
        api_key: str,
        access_token: str,
        base_url: str = "https://api.kite.trade",
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """Initializes the Zerodha Kite Connect client.

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

        headers = {
            "X-Kite-Version": self.KITE_API_VERSION,
            "Authorization": f"token {self.api_key}:{self.access_token}",
            # Content-Type is set per request based on method
        }

        self.client = httpx.AsyncClient(
            base_url=self.base_url, headers=headers, timeout=self.timeout
        )
        # Note: httpx doesn't have built-in rate limiting. For high-frequency trading,
        # consider libraries like 'aiolimiter' or custom middleware.
        # Kite Connect limits: Orders (3/s), Modify/Cancel (3/s), Reads (10/s)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite Connect API."""
        url = f"{self.base_url}{endpoint}"
        headers = self.client.headers.copy()

        # Kite API expects POST/PUT data as form-encoded, not JSON
        content_type = (
            "application/x-www-form-urlencoded"
            if method in ["POST", "PUT"]
            else "application/json"
        )
        headers["Content-Type"] = content_type

        # Filter out None values from data payload
        if data:
            processed_data = {k: v for k, v in data.items() if v is not None}
        else:
            processed_data = None

        logger.debug(f"Request: {method} {url} Params: {params} Data: {processed_data}")

        try:
            response = await self.client.request(
                method,
                endpoint, # Use relative endpoint with base_url in client
                params=params,
                data=processed_data, # Pass form data here for POST/PUT
                headers=headers,
            )

            logger.debug(
                f"Response Status: {response.status_code} Content: {response.text[:500]}..."
            )
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx
            json_response = response.json()

            # Check for API-level errors within the JSON response
            if json_response.get("status") == "error":
                logger.error(
                    f"Kite API Error: {json_response.get('message')} (Type: {json_response.get('error_type')})"
                )
                raise KiteConnectAPIError(
                    message=json_response.get("message", "Unknown API error"),
                    code=response.status_code, # Use HTTP status code if specific code not available
                )

            return json_response

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP Error: {e.response.status_code} for {e.request.url}. Response: {e.response.text}"
            )
            # Try to parse error details from response
            try:
                error_data = e.response.json()
                message = error_data.get("message", e.response.text)
                raise KiteConnectAPIError(message=message, code=e.response.status_code) from e
            except Exception:
                 # If response is not JSON or parsing fails
                 raise KiteConnectAPIError(message=e.response.text, code=e.response.status_code) from e

        except httpx.RequestError as e:
            logger.error(f"Request Error for {e.request.url}: {e}")
            raise KiteConnectAPIError(f"Request failed: {e}") from e
        except ValidationError as e:
             logger.error(f"Pydantic Validation Error: {e}")
             raise KiteConnectAPIError(f"Internal data validation error: {e}", code=400) from e
        except Exception as e:
            logger.exception(f"An unexpected error occurred during API request: {e}")
            raise KiteConnectAPIError(f"An unexpected error occurred: {e}") from e

    async def place_order(self, params: PlaceOrderParams) -> Dict[str, Any]:
        """Place an order."""
        endpoint = f"/orders/{params.variety}"
        # Exclude 'variety' from the data payload as it's in the path
        data = params.model_dump(exclude={'variety'}, exclude_unset=True)
        return await self._request("POST", endpoint, data=data)

    async def modify_order(self, params: ModifyRegularOrderParams) -> Dict[str, Any]:
        """Modify an existing order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Exclude 'variety' and 'order_id' from the data payload
        data = params.model_dump(exclude={'variety', 'order_id'}, exclude_unset=True)
        return await self._request("PUT", endpoint, data=data)

    async def cancel_order(self, params: CancelOrderParams) -> Dict[str, Any]:
        """Cancel an order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # No data payload for DELETE, params are in the path
        return await self._request("DELETE", endpoint)

    async def get_orders(self) -> Dict[str, Any]:
        """Retrieve the list of all orders."""
        endpoint = "/orders"
        return await self._request("GET", endpoint)

    async def get_order_history(self, order_id: str) -> Dict[str, Any]:
        """Retrieve the history of a specific order."""
        endpoint = f"/orders/{order_id}"
        return await self._request("GET", endpoint)

    async def get_trades(self) -> Dict[str, Any]:
        """Retrieve the list of all trades."""
        endpoint = "/trades"
        return await self._request("GET", endpoint)

    async def get_order_trades(self, order_id: str) -> Dict[str, Any]:
        """Retrieve trades for a specific order."""
        # Correct endpoint according to Kite Connect documentation
        endpoint = f"/orders/{order_id}/trades"
        return await self._request("GET", endpoint)

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("ZerodhaKiteConnectClient closed.")
