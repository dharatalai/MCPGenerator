import logging
from typing import Dict, Any, List, Optional

import httpx
from pydantic import ValidationError

from models import (
    PlaceOrderParams,
    ModifyOrderParams,
    CancelOrderParams,
    OrderIDResponse,
    Order
)

logger = logging.getLogger(__name__)

class KiteConnectError(Exception):
    """Custom exception class for Kite Connect API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

    def __str__(self):
        return f"KiteConnectError(status_code={self.status_code}): {self.message} {self.details or ''}"

class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect API."""

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
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite uses form encoding
        }
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=timeout
        )
        logger.info(f"KiteConnectClient initialized for base URL: {self.base_url}")

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Makes an asynchronous request to the Kite Connect API."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making request: {method} {url} | Params: {params} | Data: {data}")
        try:
            response = await self._client.request(method, endpoint, params=params, data=data)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
            json_response = response.json()
            logger.debug(f"Response status: {response.status_code}, Response data: {json_response}")

            # Kite API specific response structure check
            if json_response.get("status") == "error":
                error_type = json_response.get("error_type", "UnknownError")
                message = json_response.get("message", "Unknown API error")
                logger.error(f"Kite API Error ({error_type}): {message} | Status Code: {response.status_code}")
                raise KiteConnectError(message=message, status_code=response.status_code, details={"error_type": error_type})

            # Successful response usually contains a 'data' field
            return json_response.get("data", {})

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                # Attempt to parse error details from response body
                error_data = e.response.json()
                message = error_data.get("message", f"HTTP Error {status_code}")
                error_type = error_data.get("error_type", "HTTPError")
                details = {"error_type": error_type, "content": error_data}
            except Exception:
                message = f"HTTP Error {status_code}: {e.response.text[:200]}..."
                details = {"content": e.response.text}

            logger.error(f"HTTP Error: {status_code} {message}", exc_info=False) # Avoid logging full trace for HTTP errors unless debugging
            # Map common HTTP errors to KiteConnectError types
            if status_code == 400:
                raise KiteConnectError(message=f"Bad Request/Validation Error: {message}", status_code=status_code, details=details) from e
            elif status_code in [401, 403]:
                raise KiteConnectError(message=f"Authentication/Authorization Error: {message}", status_code=status_code, details=details) from e
            elif status_code == 404:
                raise KiteConnectError(message=f"Not Found: {message}", status_code=status_code, details=details) from e
            elif status_code == 429:
                raise KiteConnectError(message=f"Rate Limit Exceeded: {message}", status_code=status_code, details=details) from e
            elif status_code >= 500:
                raise KiteConnectError(message=f"Server Error: {message}", status_code=status_code, details=details) from e
            else:
                raise KiteConnectError(message=message, status_code=status_code, details=details) from e

        except httpx.RequestError as e:
            logger.error(f"Network or Request Error: {e}", exc_info=True)
            raise KiteConnectError(message=f"Network request failed: {e}") from e
        except Exception as e:
            logger.exception(f"An unexpected error occurred during API request: {e}")
            raise KiteConnectError(message=f"An unexpected error occurred: {e}") from e

    async def place_order(self, params: PlaceOrderParams) -> OrderIDResponse:
        """Place an order."""
        endpoint = f"/orders/{params.variety}"
        # Convert Pydantic model to dict, excluding None values
        data = params.dict(exclude={'variety'}, exclude_none=True)
        try:
            response_data = await self._request("POST", endpoint, data=data)
            return OrderIDResponse(**response_data)
        except ValidationError as e:
            logger.error(f"Response validation error for place_order: {e}")
            raise KiteConnectError(message="Invalid response format from API", details=str(e))

    async def modify_order(self, params: ModifyOrderParams) -> OrderIDResponse:
        """Modify an existing order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Only include fields relevant for modification, exclude identifiers and None
        data = params.dict(exclude={'variety', 'order_id'}, exclude_none=True)
        try:
            response_data = await self._request("PUT", endpoint, data=data)
            return OrderIDResponse(**response_data)
        except ValidationError as e:
            logger.error(f"Response validation error for modify_order: {e}")
            raise KiteConnectError(message="Invalid response format from API", details=str(e))

    async def cancel_order(self, params: CancelOrderParams) -> OrderIDResponse:
        """Cancel an existing order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        query_params = {}
        if params.parent_order_id:
            query_params['parent_order_id'] = params.parent_order_id

        try:
            response_data = await self._request("DELETE", endpoint, params=query_params)
            return OrderIDResponse(**response_data)
        except ValidationError as e:
            logger.error(f"Response validation error for cancel_order: {e}")
            raise KiteConnectError(message="Invalid response format from API", details=str(e))

    async def get_orders(self) -> List[Order]:
        """Retrieve the list of orders for the day."""
        endpoint = "/orders"
        try:
            response_data = await self._request("GET", endpoint)
            # response_data is expected to be a list of order dictionaries
            if not isinstance(response_data, list):
                 logger.error(f"Unexpected response format for get_orders: expected list, got {type(response_data)}")
                 raise KiteConnectError(message="Invalid response format from API: Expected a list of orders.", details=response_data)

            orders = [Order(**order_data) for order_data in response_data]
            return orders
        except ValidationError as e:
            logger.error(f"Response validation error for get_orders: {e}")
            raise KiteConnectError(message="Invalid order data format in API response", details=str(e))

    async def close(self):
        """Closes the underlying HTTP client."""
        await self._client.aclose()
        logger.info("KiteConnectClient closed.")
