import httpx
import logging
from typing import Dict, Any, Optional, List

from models import PlaceOrderInput, ModifyOrderInput, CancelOrderInput

logger = logging.getLogger(__name__)

# Custom exception for Kite API specific errors
class KiteApiException(Exception):
    def __init__(self, message: str, error_type: Optional[str] = None, status_code: Optional[int] = None):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        super().__init__(f"Kite API Error ({error_type or 'Unknown'}): {message}")

class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect Orders API (v3)."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade", timeout: float = 30.0):
        """
        Initializes the Kite Connect client.

        Args:
            api_key: Your Kite Connect API key.
            access_token: The access token obtained after successful login.
            base_url: The base URL for the Kite API (defaults to production).
            timeout: Default timeout for HTTP requests in seconds.
        """
        if not api_key or not access_token:
            raise ValueError("API key and access token are required.")
        
        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url
        self.timeout = timeout
        
        headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite API often uses form encoding
        }
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout
        )
        logger.info(f"KiteConnectClient initialized for base URL: {self.base_url}")

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite API."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Sending {method} request to {url}")
        logger.debug(f"Params: {params}")
        logger.debug(f"Data: {data}")
        
        try:
            response = await self.client.request(method, endpoint, params=params, data=data)
            
            # Check for HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            json_response = response.json()
            logger.debug(f"Received successful response ({response.status_code}) from {url}: {json_response}")
            
            # Check for Kite API specific errors within the JSON response
            if json_response.get("status") == "error":
                error_type = json_response.get("error_type", "UnknownError")
                message = json_response.get("message", "No error message provided.")
                logger.error(f"Kite API error response from {url}: {error_type} - {message}")
                raise KiteApiException(message=message, error_type=error_type, status_code=response.status_code)
                
            return json_response

        except httpx.HTTPStatusError as e:
            # Attempt to parse error details from response body if available
            error_details = "No details available."
            error_type = "HTTPError"
            try:
                error_data = e.response.json()
                error_details = error_data.get("message", e.response.text)
                error_type = error_data.get("error_type", error_type)
            except Exception:
                error_details = e.response.text # Fallback to raw text
            
            logger.error(f"HTTP error {e.response.status_code} from {url}: {error_details}")
            # Raise KiteApiException for consistency in handling API-related issues
            raise KiteApiException(message=error_details, error_type=error_type, status_code=e.response.status_code) from e

        except httpx.RequestError as e:
            logger.error(f"Network or request error contacting {url}: {e}")
            raise KiteApiException(message=f"Network error: {e}", error_type="NetworkError") from e
            
        except Exception as e:
            logger.exception(f"An unexpected error occurred during request to {url}: {e}")
            raise KiteApiException(message=f"Unexpected error: {e}", error_type="ClientError") from e

    async def place_order(self, order_data: PlaceOrderInput) -> Dict[str, Any]:
        """Places an order."""
        endpoint = f"/orders/{order_data.variety.value}"
        # Convert Pydantic model to dict, excluding None values and the path parameter 'variety'
        payload = order_data.dict(exclude={'variety'}, exclude_none=True)
        logger.info(f"Placing order: {payload}")
        return await self._request("POST", endpoint, data=payload)

    async def modify_order(self, order_data: ModifyOrderInput) -> Dict[str, Any]:
        """Modifies an existing order."""
        endpoint = f"/orders/{order_data.variety.value}/{order_data.order_id}"
        # Convert Pydantic model to dict, excluding None values and path parameters
        payload = order_data.dict(exclude={'variety', 'order_id'}, exclude_none=True)
        logger.info(f"Modifying order {order_data.order_id}: {payload}")
        return await self._request("PUT", endpoint, data=payload)

    async def cancel_order(self, order_data: CancelOrderInput) -> Dict[str, Any]:
        """Cancels an existing order."""
        endpoint = f"/orders/{order_data.variety.value}/{order_data.order_id}"
        # Parent order ID might be needed in payload for CO legs
        payload = {}
        if order_data.parent_order_id:
             payload['parent_order_id'] = order_data.parent_order_id
        logger.info(f"Cancelling order {order_data.order_id} with payload: {payload}")
        # Note: DELETE requests might not typically have a body, but check Kite docs if parent_order_id needs to be sent differently.
        # Assuming it's sent as form data if needed.
        return await self._request("DELETE", endpoint, data=payload if payload else None)

    async def get_orders(self) -> Dict[str, Any]:
        """Retrieves the list of orders for the day."""
        endpoint = "/orders"
        logger.info("Retrieving orders list.")
        # This endpoint uses GET, no data payload needed
        return await self._request("GET", endpoint)

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("KiteConnectClient closed.")
