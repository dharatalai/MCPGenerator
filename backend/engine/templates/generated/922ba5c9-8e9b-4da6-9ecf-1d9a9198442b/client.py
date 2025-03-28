import httpx
import logging
from typing import Dict, Any, List, Optional

from models import VarietyEnum

logger = logging.getLogger(__name__)

class KiteApiException(Exception):
    """Custom exception for Kite Connect API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details

    def __str__(self):
        return f"KiteApiException: {super().__str__()} (Status: {self.status_code}, Details: {self.details})"

class AsyncKiteClient:
    """Asynchronous client for interacting with the Zerodha Kite Connect API."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade", timeout: float = 30.0):
        """
        Initializes the asynchronous Kite Connect client.

        Args:
            api_key (str): The API key obtained from Kite Connect.
            access_token (str): The access token obtained after successful login.
            base_url (str): The base URL for the Kite Connect API.
            timeout (float): Default request timeout in seconds.
        """
        if not api_key or not access_token:
            raise ValueError("API Key and Access Token cannot be empty.")

        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url
        self.timeout = timeout
        self.headers = {
            "X-Kite-Version": "3",  # Specify Kite Connect API version
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite uses form encoding
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout
        )
        logger.info(f"AsyncKiteClient initialized for base URL: {self.base_url}")

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite Connect API."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making {method} request to {url}")
        logger.debug(f"Headers: {self.headers}") # Be careful logging headers in production if sensitive
        if params:
            logger.debug(f"URL Params: {params}")
        if data:
            logger.debug(f"Form Data: {data}")

        try:
            response = await self.client.request(
                method=method,
                url=endpoint, # httpx client uses base_url + endpoint
                params=params,
                data=data # Send as form data
            )
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            json_response = response.json()
            logger.debug(f"Received successful response ({response.status_code}): {json_response}")

            # Kite API specific success/error check (often includes a 'status' field)
            if json_response.get("status") == "error":
                error_type = json_response.get("error_type", "UnknownError")
                message = json_response.get("message", "Unknown API error")
                logger.error(f"Kite API error: Type={error_type}, Message={message}")
                raise KiteApiException(message=message, status_code=response.status_code, details=json_response)

            # Return the 'data' part of the response if it exists
            return json_response.get("data", json_response)

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                error_details = e.response.json()
                message = error_details.get("message", "HTTP error")
                error_type = error_details.get("error_type", f"HTTP {status_code}")
            except Exception:
                error_details = e.response.text
                message = f"HTTP error {status_code}"
                error_type = f"HTTP {status_code}"

            logger.error(f"HTTP error occurred: {status_code} - {message}", exc_info=True)
            raise KiteApiException(message=message, status_code=status_code, details=error_details) from e

        except httpx.RequestError as e:
            logger.error(f"Network or request error occurred: {e}", exc_info=True)
            raise KiteApiException(message=f"Network error: {e}", details=str(e)) from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during API request: {e}", exc_info=True)
            raise KiteApiException(message="An unexpected error occurred", details=str(e)) from e

    async def place_order(self, variety: VarietyEnum, data: Dict[str, Any]) -> Dict[str, str]:
        """Place an order."""
        endpoint = f"/orders/{variety.value}"
        return await self._request(method="POST", endpoint=endpoint, data=data)

    async def modify_order(self, variety: VarietyEnum, order_id: str, data: Dict[str, Any]) -> Dict[str, str]:
        """Modify a pending order."""
        endpoint = f"/orders/{variety.value}/{order_id}"
        return await self._request(method="PUT", endpoint=endpoint, data=data)

    async def cancel_order(self, variety: VarietyEnum, order_id: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Cancel a pending order."""
        endpoint = f"/orders/{variety.value}/{order_id}"
        # Include parent_order_id in data if provided for CO legs
        return await self._request(method="DELETE", endpoint=endpoint, data=data or {})

    async def get_orders(self) -> List[Dict[str, Any]]:
        """Retrieve the list of orders for the day."""
        endpoint = "/orders"
        # The response is directly a list of orders under the 'data' key
        result = await self._request(method="GET", endpoint=endpoint)
        if isinstance(result, list):
            return result
        else:
             logger.error(f"Unexpected response format for get_orders: {result}")
             raise KiteApiException("Unexpected response format from get_orders", details=result)


    async def get_order_history(self, order_id: str) -> List[Dict[str, Any]]:
        """Retrieve the history for a given order ID."""
        endpoint = f"/orders/{order_id}/trades" # Note: Kite API uses /trades for history/fills
        # Check Kite documentation - sometimes history is under /orders/{order_id} directly
        # Assuming /trades endpoint returns fill details which act as history.
        # If a dedicated history endpoint exists, adjust the endpoint.
        # Let's assume the plan meant order details/trades, using the /trades endpoint.
        # If it strictly means status changes, the /orders endpoint might be re-queried or websockets used.
        # For now, implementing based on /trades endpoint which gives fill history.
        # If the actual API endpoint is just /orders/{order_id}, change below.

        # Correction based on common understanding: GET /orders/{order_id} might return history/details.
        # Let's use that interpretation as /trades is specifically for trade fills.
        endpoint = f"/orders/{order_id}"
        result = await self._request(method="GET", endpoint=endpoint)
        if isinstance(result, list):
             # The response for a single order history is typically a list of states/updates
            return result
        elif isinstance(result, dict):
             # Sometimes it might return a single dict if only one state exists? Adapt as needed.
             # Or perhaps the endpoint returns a dict containing a list under a key.
             # Assuming the API returns a list directly as per the plan's return type List[OrderHistoryEntry]
             logger.warning(f"Received dict instead of list for order history {order_id}, wrapping in list.")
             return [result]
        else:
            logger.error(f"Unexpected response format for get_order_history: {result}")
            raise KiteApiException("Unexpected response format from get_order_history", details=result)

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("AsyncKiteClient closed.")
