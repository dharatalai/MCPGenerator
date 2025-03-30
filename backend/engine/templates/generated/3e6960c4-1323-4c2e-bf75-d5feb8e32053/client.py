import logging
from typing import Dict, Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from models import PlaceOrderParams, ModifyOrderParams

logger = logging.getLogger(__name__)

# --- Custom Exceptions --- #

class KiteConnectError(Exception):
    """Base exception for Kite Connect API errors."""
    def __init__(self, message="An API error occurred", status_code=None, error_type=None):
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(f"{error_type or 'API Error'} (HTTP {status_code}): {message}")

class AuthenticationError(KiteConnectError):
    """Error related to authentication (invalid API key, access token)."""
    pass

class InvalidInputError(KiteConnectError):
    """Error due to invalid input parameters."""
    pass

class InsufficientFundsError(KiteConnectError):
    """Error when there are not enough funds for the order."""
    pass

class NetworkError(KiteConnectError):
    """Error related to network connectivity issues."""
    pass

class RateLimitError(KiteConnectError):
    """Error when API rate limits are exceeded."""
    pass

class ExchangeError(KiteConnectError):
    """Error reported by the exchange."""
    pass

class OrderNotFoundError(KiteConnectError):
    """Error when trying to modify/cancel a non-existent order."""
    pass

class OrderNotModifiableError(KiteConnectError):
    """Error when trying to modify an order that is not in a modifiable state."""
    pass

class GeneralAPIError(KiteConnectError):
    """General or unclassified API errors."""
    pass

# Mapping from Kite error types (strings) to custom exception classes
KITE_ERROR_MAP = {
    # General
    "InputException": InvalidInputError,
    "TokenException": AuthenticationError,
    "GeneralException": GeneralAPIError,
    "NetworkException": NetworkError, # Assuming httpx might raise this, map Kite's equivalent if exists
    "DataException": GeneralAPIError, # Or could be InvalidInputError depending on context

    # Order specific
    "OrderException": GeneralAPIError, # Base for order errors, specific ones below
    "MarginException": InsufficientFundsError,
    "FundsException": InsufficientFundsError,
    "QuantityException": InvalidInputError,
    "PriceException": InvalidInputError,
    "TriggerPriceException": InvalidInputError,
    "OrderNotFoundException": OrderNotFoundError, # Hypothetical, check actual Kite errors
    "OrderModificationException": OrderNotModifiableError, # Hypothetical

    # Exchange specific
    "ExchangeException": ExchangeError,

    # Rate limiting
    "NetworkException": RateLimitError, # Kite uses NetworkException for rate limits often
    # Add more specific mappings based on Kite Connect v3 documentation
}

# Mapping from HTTP status codes to custom exception classes
HTTP_STATUS_MAP = {
    400: InvalidInputError, # Bad Request
    401: AuthenticationError, # Unauthorized (likely token issue)
    403: AuthenticationError, # Forbidden (API key issue or permissions)
    404: OrderNotFoundError, # Not Found (often for modifying non-existent order)
    405: GeneralAPIError, # Method Not Allowed
    429: RateLimitError, # Too Many Requests
    500: GeneralAPIError, # Internal Server Error
    502: ExchangeError, # Bad Gateway (often exchange issues)
    503: ExchangeError, # Service Unavailable (often exchange issues)
    504: NetworkError, # Gateway Timeout
}

class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect API v3 Orders.

    Handles request formation, authentication, and basic error handling.
    """
    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade", timeout: float = 30.0):
        """Initializes the Kite Connect client.

        Args:
            api_key: Your Kite Connect API key.
            access_token: The access token obtained after successful login.
            base_url: The base URL for the Kite Connect API.
            timeout: Request timeout in seconds.
        """
        if not api_key or not access_token:
            raise ValueError("API Key and Access Token cannot be empty.")

        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url
        self.timeout = timeout
        self._headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite API expects form data
        }
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=self.timeout
        )

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type((NetworkError, RateLimitError)))
    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite API with error handling and retries.

        Args:
            method: HTTP method (e.g., 'POST', 'PUT', 'GET', 'DELETE').
            endpoint: API endpoint path (e.g., '/orders/regular').
            data: Dictionary of form data for POST/PUT requests.

        Returns:
            The JSON response data as a dictionary.

        Raises:
            KiteConnectError: If the API returns an error or the request fails.
        """
        url = f"{self.base_url}{endpoint}"
        try:
            logger.debug(f"Sending {method} request to {url} with data: {data}")
            response = await self._client.request(method, endpoint, data=data)

            # Check for HTTP errors
            response.raise_for_status()

            # Successful response
            json_response = response.json()
            logger.debug(f"Received successful response ({response.status_code}) from {url}: {json_response}")

            # Kite API specific success check (often has a 'data' field)
            if 'status' in json_response and json_response['status'] == 'success':
                return json_response.get('data', {}) # Return the nested data part
            elif 'data' in json_response: # Handle cases where status might not be present but data is
                 return json_response.get('data', {})
            else:
                # If structure is unexpected but status was 2xx
                logger.warning(f"Unexpected successful response structure from {url}: {json_response}")
                return json_response # Return the full response

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                error_data = e.response.json()
                message = error_data.get('message', 'Unknown API error')
                error_type = error_data.get('error_type', 'UnknownErrorType')
                logger.error(f"Kite API Error ({status_code}) from {url}: {message} (Type: {error_type})")

                # Map Kite error type first, then HTTP status code
                exception_class = KITE_ERROR_MAP.get(error_type, HTTP_STATUS_MAP.get(status_code, GeneralAPIError))
                raise exception_class(message=message, status_code=status_code, error_type=error_type) from e

            except Exception as json_error:
                # If parsing error response fails
                message = e.response.text or f"HTTP Error {status_code}"
                error_type = 'UnknownErrorType'
                logger.error(f"Kite API Error ({status_code}) from {url}. Failed to parse error response: {json_error}. Response text: {message}")
                exception_class = HTTP_STATUS_MAP.get(status_code, GeneralAPIError)
                raise exception_class(message=message, status_code=status_code, error_type=error_type) from e

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out for {method} {url}: {e}")
            raise NetworkError(message="Request timed out", status_code=None, error_type="TimeoutError") from e
        except httpx.NetworkError as e:
            logger.error(f"Network error for {method} {url}: {e}")
            # Check if it's a rate limit error disguised as NetworkException by Kite
            if "rate limit" in str(e).lower(): # Basic check, might need refinement
                 raise RateLimitError(message="Rate limit likely exceeded", status_code=429, error_type="RateLimitError") from e
            raise NetworkError(message=f"Network error: {e}", status_code=None, error_type="NetworkError") from e
        except Exception as e:
            logger.exception(f"Unexpected error during request to {url}: {e}")
            raise GeneralAPIError(message=f"An unexpected client error occurred: {e}", status_code=None, error_type="ClientError") from e

    async def place_order_async(self, params: PlaceOrderParams) -> Dict[str, str]:
        """Places an order asynchronously.

        Args:
            params: An instance of PlaceOrderParams containing order details.

        Returns:
            A dictionary containing the 'order_id'.
        """
        endpoint = f"/orders/{params.variety}"
        # Prepare form data, excluding None values and the 'variety' field itself
        data = {k: v for k, v in params.dict(exclude={'variety'}).items() if v is not None}

        logger.info(f"Placing order via endpoint: {endpoint}")
        response_data = await self._request("POST", endpoint, data=data)

        if 'order_id' not in response_data:
            logger.error(f"'order_id' not found in response for place order: {response_data}")
            raise GeneralAPIError(message="'order_id' missing from successful place order response", error_type="ResponseFormatError")

        return {"order_id": response_data['order_id']}

    async def modify_order_async(self, params: ModifyOrderParams) -> Dict[str, str]:
        """Modifies a pending order asynchronously.

        Args:
            params: An instance of ModifyOrderParams containing modification details.

        Returns:
            A dictionary containing the 'order_id'.
        """
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Prepare form data, excluding None values and path parameters ('variety', 'order_id')
        data = {k: v for k, v in params.dict(exclude={'variety', 'order_id'}).items() if v is not None}

        logger.info(f"Modifying order {params.order_id} via endpoint: {endpoint}")
        response_data = await self._request("PUT", endpoint, data=data)

        if 'order_id' not in response_data:
            logger.error(f"'order_id' not found in response for modify order: {response_data}")
            raise GeneralAPIError(message="'order_id' missing from successful modify order response", error_type="ResponseFormatError")

        return {"order_id": response_data['order_id']}

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self._client.aclose()
        logger.info("Kite Connect client closed.")
