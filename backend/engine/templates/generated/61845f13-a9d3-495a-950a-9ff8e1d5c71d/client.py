import httpx
import logging
from typing import Dict, Any, Optional

from models import (
    PlaceOrderParams,
    ModifyOrderParams,
    CancelOrderParams,
    KiteConnectError,
    AuthenticationError,
    InvalidInputError,
    InsufficientFundsError,
    NetworkError,
    RateLimitError,
    ExchangeError,
    OrderPlacementError,
    OrderModificationError,
    OrderCancellationError,
    OrderNotFoundError,
    GeneralError
)

logger = logging.getLogger(__name__)

class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect V3 Orders API."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade", timeout: float = 30.0):
        """
        Initializes the KiteConnectClient.

        Args:
            api_key: Your Kite Connect API key.
            access_token: The access token obtained after login.
            base_url: The base URL for the Kite Connect API.
            timeout: Default timeout for HTTP requests in seconds.
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
            "Content-Type": "application/x-www-form-urlencoded" # Kite API uses form encoding
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout
        )

    async def close(self):
        """Closes the underlying HTTP client."""
        await self.client.aclose()

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Makes an asynchronous HTTP request to the Kite Connect API.

        Args:
            method: HTTP method (e.g., 'GET', 'POST', 'PUT', 'DELETE').
            endpoint: API endpoint path (e.g., '/orders/regular').
            data: Dictionary payload for POST/PUT requests (will be form-encoded).

        Returns:
            The JSON response from the API as a dictionary.

        Raises:
            Various KiteConnectError subclasses based on the response or network issues.
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Request: {method} {url} Data: {data}")

        try:
            response = await self.client.request(method, endpoint, data=data)
            logger.debug(f"Response Status: {response.status_code} Body: {response.text}")
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
            return response.json()

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {method} {url} - {e}")
            raise NetworkError(f"Request timed out: {e}", details=str(e))
        except httpx.RequestError as e:
            # Includes connection errors, etc.
            logger.error(f"Request error: {method} {url} - {e}")
            raise NetworkError(f"HTTP request failed: {e}", details=str(e))
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                error_details = e.response.json()
                message = error_details.get("message", "No specific message")
                error_type = error_details.get("error_type", "UnknownErrorType") # Kite specific error type
            except Exception:
                error_details = e.response.text
                message = f"HTTP {status_code} Error"
                error_type = "UnknownErrorType"

            logger.error(f"HTTP error: {method} {url} - Status: {status_code}, Response: {error_details}")

            # Map status codes and potentially error_type to specific exceptions
            if status_code == 400:
                # Could be InvalidInputError or potentially ExchangeError, OrderNotFoundError etc.
                # Check error_type if possible
                if "InputException" in error_type:
                    raise InvalidInputError(message=message, details=error_details)
                elif "OrderException" in error_type: # Example, adjust based on actual Kite errors
                     raise OrderPlacementError(message=message, details=error_details)
                else:
                    raise InvalidInputError(message=message, details=error_details) # Default for 400
            elif status_code == 403:
                raise AuthenticationError(message=message, details=error_details)
            elif status_code == 404:
                 # Often used for Order Not Found during modify/cancel
                 raise OrderNotFoundError(message=message, details=error_details)
            elif status_code == 429:
                raise RateLimitError(message=message, details=error_details)
            elif status_code == 500:
                # Could be GeneralError, ExchangeError, OrderPlacementError etc.
                if "ExchangeException" in error_type: # Example
                    raise ExchangeError(message=message, details=error_details)
                else:
                    raise GeneralError(message=message, status_code=status_code, details=error_details)
            elif status_code in [502, 503, 504]:
                raise GeneralError(message=message, status_code=status_code, details=error_details)
            else:
                # Catch-all for other unexpected HTTP errors
                raise KiteConnectError(message=f"Unhandled HTTP error: {status_code}", status_code=status_code, details=error_details)
        except Exception as e:
            # Catch-all for non-HTTP exceptions (e.g., JSON decoding errors)
            logger.exception(f"Unexpected error during request: {method} {url} - {e}")
            raise KiteConnectError(f"An unexpected error occurred: {e}", details=str(e))

    async def place_order(self, params: PlaceOrderParams) -> Dict[str, Any]:
        """
        Places an order using the Kite Connect API.

        Args:
            params: A PlaceOrderParams object containing order details.

        Returns:
            The API response dictionary, typically containing {'status': 'success', 'data': {'order_id': '...'}}.
        """
        endpoint = f"/orders/{params.variety}"
        # Exclude 'variety' from the form data, as it's in the path
        data = params.dict(exclude={'variety'}, exclude_none=True)
        # Convert boolean/None/list values if necessary for form encoding
        # httpx handles basic types well, but check Kite docs for specifics
        try:
            return await self._request("POST", endpoint, data=data)
        except KiteConnectError as e:
            # Add context specific to the operation
            if isinstance(e, InvalidInputError):
                 logger.error(f"Invalid input placing order: {e.message} - {e.details}")
            # Re-raise the specific error
            raise e
        except Exception as e:
            logger.exception("Unexpected error in place_order wrapper")
            raise OrderPlacementError(f"Unexpected error during order placement: {e}", details=str(e))


    async def modify_order(self, params: ModifyOrderParams) -> Dict[str, Any]:
        """
        Modifies an existing order using the Kite Connect API.

        Args:
            params: A ModifyOrderParams object containing modification details.

        Returns:
            The API response dictionary, typically containing {'status': 'success', 'data': {'order_id': '...'}}.
        """
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Exclude path parameters from the form data
        data = params.dict(exclude={'variety', 'order_id'}, exclude_none=True)
        try:
            return await self._request("PUT", endpoint, data=data)
        except KiteConnectError as e:
            if isinstance(e, OrderNotFoundError):
                 logger.warning(f"Attempted to modify non-existent order {params.order_id}: {e.message}")
            raise e
        except Exception as e:
            logger.exception("Unexpected error in modify_order wrapper")
            raise OrderModificationError(f"Unexpected error during order modification: {e}", details=str(e))


    async def cancel_order(self, params: CancelOrderParams) -> Dict[str, Any]:
        """
        Cancels an existing order using the Kite Connect API.

        Args:
            params: A CancelOrderParams object containing the order details.

        Returns:
            The API response dictionary, typically containing {'status': 'success', 'data': {'order_id': '...'}}.
        """
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # No data payload for DELETE usually, but check API spec if needed
        try:
            return await self._request("DELETE", endpoint)
        except KiteConnectError as e:
            if isinstance(e, OrderNotFoundError):
                 logger.warning(f"Attempted to cancel non-existent order {params.order_id}: {e.message}")
            raise e
        except Exception as e:
            logger.exception("Unexpected error in cancel_order wrapper")
            raise OrderCancellationError(f"Unexpected error during order cancellation: {e}", details=str(e))
