import httpx
import logging
import os
from typing import Dict, Any, List, Optional
from models import (
    PlaceOrderParams, ModifyOrderParams, CancelOrderParams,
    GetOrderHistoryParams, Order, OrderHistoryEntry, OrderResponse
)

logger = logging.getLogger(__name__)

KITE_API_VERSION = "3"

class KiteConnectError(Exception):
    """Custom exception for Kite Connect API errors."""
    def __init__(self, status_code: int, error_type: str, message: str):
        self.status_code = status_code
        self.error_type = error_type
        self.message = message
        super().__init__(f"Kite API Error ({status_code} - {error_type}): {message}")

class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect v3 API."""

    def __init__(self):
        self.api_key = os.getenv("KITE_API_KEY")
        self.access_token = os.getenv("KITE_ACCESS_TOKEN")
        self.base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")

        if not self.api_key or not self.access_token:
            raise ValueError("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")

        self.headers = {
            "X-Kite-Version": KITE_API_VERSION,
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite uses form encoding
        }
        # Note: Rate limits are 3 requests/second per user per app.
        # Implementing client-side throttling is complex and not included here.
        # Ensure your usage pattern respects these limits.
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0 # Set a reasonable timeout
        )

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite API."""
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Sending {method} request to {url}")
        logger.debug(f"Headers: {self.headers}")
        if data:
            # Filter out None values before sending
            filtered_data = {k: v for k, v in data.items() if v is not None}
            logger.debug(f"Payload (form data): {filtered_data}")
        else:
            filtered_data = None
            logger.debug("No payload.")

        try:
            response = await self.client.request(method, endpoint, params=params, data=filtered_data)
            logger.info(f"Received response with status code: {response.status_code}")
            logger.debug(f"Response content: {response.text}")

            # Check for non-JSON or empty responses before parsing
            if not response.text:
                 if 200 <= response.status_code < 300:
                     logger.warning(f"Received empty response body with status {response.status_code} for {method} {endpoint}")
                     # Handle cases like DELETE success which might return 200 OK with no body
                     # This behavior might need adjustment based on actual API responses
                     return {"status": "success", "data": {}} # Assume success if status is 2xx
                 else:
                     raise KiteConnectError(response.status_code, "EmptyResponse", "Received empty response from API")

            response_json = response.json()

            # Raise exceptions for HTTP errors (4xx, 5xx)
            response.raise_for_status()

            # Check Kite specific error structure (if applicable, based on observed API behavior)
            if response_json.get("status") == "error":
                error_type = response_json.get("error_type", "UnknownError")
                message = response_json.get("message", "No error message provided.")
                logger.error(f"Kite API Error: Type={error_type}, Message={message}")
                raise KiteConnectError(response.status_code, error_type, message)

            return response_json

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            # Try to parse error details from Kite's response format
            try:
                error_data = e.response.json()
                error_type = error_data.get("error_type", f"HTTP{e.response.status_code}")
                message = error_data.get("message", e.response.text)
                raise KiteConnectError(e.response.status_code, error_type, message) from e
            except Exception:
                 # If parsing fails, raise a generic error
                 raise KiteConnectError(e.response.status_code, f"HTTP{e.response.status_code}", e.response.text) from e
        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise KiteConnectError(408, "Timeout", "The request to Kite API timed out.") from e
        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting {e.request.url!r}: {e}")
            raise KiteConnectError(500, "RequestError", f"Failed to connect or send request to Kite API: {e}") from e
        except Exception as e:
            logger.exception(f"An unexpected error occurred during API request: {e}") # Use exception for stack trace
            raise KiteConnectError(500, "UnexpectedError", f"An unexpected error occurred: {e}") from e

    async def place_order(self, params: PlaceOrderParams) -> OrderResponse:
        """Places an order."""
        endpoint = f"/orders/{params.variety}"
        # Convert Pydantic model to dict, excluding 'variety' as it's in the path
        # Use exclude_unset=True to only send provided optional fields
        data = params.model_dump(exclude={'variety'}, exclude_unset=True)
        response_data = await self._request("POST", endpoint, data=data)
        # Assuming the response structure is {'status': 'success', 'data': {'order_id': '...'}}
        if response_data.get("status") == "success" and "order_id" in response_data.get("data", {}):
            return OrderResponse(**response_data["data"])
        else:
            logger.error(f"Place order failed or returned unexpected format: {response_data}")
            raise KiteConnectError(500, "InvalidResponse", f"Unexpected response format from place_order: {response_data}")

    async def modify_order(self, params: ModifyOrderParams) -> OrderResponse:
        """Modifies an existing order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Convert Pydantic model to dict, excluding path params and unset optional fields
        data = params.model_dump(exclude={'variety', 'order_id'}, exclude_unset=True)
        response_data = await self._request("PUT", endpoint, data=data)
        if response_data.get("status") == "success" and "order_id" in response_data.get("data", {}):
            return OrderResponse(**response_data["data"])
        else:
            logger.error(f"Modify order failed or returned unexpected format: {response_data}")
            raise KiteConnectError(500, "InvalidResponse", f"Unexpected response format from modify_order: {response_data}")

    async def cancel_order(self, params: CancelOrderParams) -> OrderResponse:
        """Cancels an existing order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Pass parent_order_id if provided (as form data for DELETE)
        data = {}
        if params.parent_order_id:
            data['parent_order_id'] = params.parent_order_id
        
        response_data = await self._request("DELETE", endpoint, data=data if data else None)
        # Successful DELETE might return {'status': 'success', 'data': {'order_id': '...'}}
        # Or potentially just 200 OK with minimal/no body - _request handles basic 2xx empty body case
        if response_data.get("status") == "success" and "order_id" in response_data.get("data", {}):
             # Use the original order_id for the response model if API returns it
            return OrderResponse(order_id=response_data["data"].get("order_id", params.order_id))
        elif response_data.get("status") == "success": # Handle case where data might be empty but status is success
             logger.warning(f"Cancel order returned success status but no order_id in data for {params.order_id}")
             return OrderResponse(order_id=params.order_id) # Return the ID we tried to cancel
        else:
            logger.error(f"Cancel order failed or returned unexpected format: {response_data}")
            raise KiteConnectError(500, "InvalidResponse", f"Unexpected response format from cancel_order: {response_data}")

    async def get_orders(self) -> List[Order]:
        """Retrieves the list of orders for the day."""
        endpoint = "/orders"
        response_data = await self._request("GET", endpoint)
        # Assuming response is {'status': 'success', 'data': [...]}
        if response_data.get("status") == "success" and isinstance(response_data.get("data"), list):
            # Parse each item in the list using the Order model
            # Use parse_obj_as for robust parsing of list of models
            from pydantic import parse_obj_as
            try:
                return parse_obj_as(List[Order], response_data["data"])
            except Exception as e:
                 logger.error(f"Failed to parse list of orders: {e}")
                 raise KiteConnectError(500, "ParsingError", f"Could not parse order list: {e}")
        else:
            logger.error(f"Get orders failed or returned unexpected format: {response_data}")
            raise KiteConnectError(500, "InvalidResponse", f"Unexpected response format from get_orders: {response_data}")

    async def get_order_history(self, params: GetOrderHistoryParams) -> List[OrderHistoryEntry]:
        """Retrieves the history for a specific order."""
        endpoint = f"/orders/{params.order_id}"
        response_data = await self._request("GET", endpoint)
        # Assuming response is {'status': 'success', 'data': [...]}
        if response_data.get("status") == "success" and isinstance(response_data.get("data"), list):
            from pydantic import parse_obj_as
            try:
                return parse_obj_as(List[OrderHistoryEntry], response_data["data"])
            except Exception as e:
                 logger.error(f"Failed to parse order history: {e}")
                 raise KiteConnectError(500, "ParsingError", f"Could not parse order history list: {e}")
        else:
            logger.error(f"Get order history failed or returned unexpected format: {response_data}")
            raise KiteConnectError(500, "InvalidResponse", f"Unexpected response format from get_order_history: {response_data}")
