import logging
from typing import Dict, Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from models import PlaceOrderParams, ModifyOrderParams

logger = logging.getLogger(__name__)

# --- Custom Exceptions ---

class KiteConnectError(Exception):
    """Base exception for Kite Connect client errors."""
    def __init__(self, message="An error occurred with the Kite Connect API", status_code: Optional[int] = None, error_type: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type # Kite specific error type if available
        super().__init__(self.message)

    def __str__(self):
        return f"{self.__class__.__name__}(status_code={self.status_code}, error_type={self.error_type}): {self.message}"

class AuthenticationError(KiteConnectError):
    """Error related to authentication (invalid API key, access token)."""
    pass

class ValidationError(KiteConnectError):
    """Error related to invalid input parameters."""
    pass

class OrderNotFoundOrCompletedError(KiteConnectError):
    """Error when trying to modify/cancel an order that doesn't exist or is already completed."""
    pass

class InsufficientFundsError(KiteConnectError):
    """Error due to insufficient funds or margin."""
    pass

class NetworkError(KiteConnectError):
    """Error related to network connectivity issues."""
    pass

class RateLimitError(KiteConnectError):
    """Error due to exceeding API rate limits."""
    pass

class ExchangeError(KiteConnectError):
    """Error reported by the exchange."""
    pass

class GeneralAPIError(KiteConnectError):
    """General or unknown errors from the Kite API."""
    pass

# --- Kite Connect Client ---

class KiteConnectClient:
    """Asynchronous client for interacting with the Zerodha Kite Connect API v3."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade", timeout: float = 30.0):
        """Initialize the client.

        Args:
            api_key: Your Kite Connect API key.
            access_token: The access token obtained after successful login.
            base_url: The base URL for the Kite Connect API.
            timeout: Default request timeout in seconds.
        """
        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url
        self.timeout = timeout
        self._headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite uses form data
        }
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=self.timeout
        )
        logger.info(f"KiteConnectClient initialized for base URL: {self.base_url}")

    def _map_error(self, status_code: int, response_data: Optional[Dict[str, Any]] = None) -> KiteConnectError:
        """Maps HTTP status codes and response data to specific KiteConnectError exceptions."""
        message = "Unknown API error"
        error_type = "UnknownError"
        if response_data and isinstance(response_data.get('message'), str):
            message = response_data['message']
        if response_data and isinstance(response_data.get('error_type'), str):
            error_type = response_data['error_type']

        if status_code == 400:
            # Often validation errors, but can be others
            if error_type == "InputException":
                return ValidationError(message, status_code, error_type)
            elif error_type == "OrderException": # e.g., margin errors
                 # Check for specific messages if needed
                 if "margin" in message.lower() or "funds" in message.lower():
                      return InsufficientFundsError(message, status_code, error_type)
                 return ExchangeError(message, status_code, error_type)
            return ValidationError(message, status_code, error_type) # Default to validation for 400
        elif status_code == 403:
            return AuthenticationError(message, status_code, error_type)
        elif status_code == 404:
            return OrderNotFoundOrCompletedError(message, status_code, error_type)
        elif status_code == 429:
            return RateLimitError(message, status_code, error_type)
        elif status_code == 500:
            return GeneralAPIError(message, status_code, error_type)
        elif status_code == 502 or status_code == 503 or status_code == 504:
             return ExchangeError(f"Exchange/Gateway Error: {message}", status_code, error_type)
        else:
            return GeneralAPIError(f"Unexpected HTTP status {status_code}: {message}", status_code, error_type)

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type((NetworkError, RateLimitError)))
    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous request to the Kite API with error handling and retries."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making request: {method} {url}, Data: {data}")

        try:
            response = await self._client.request(method, endpoint, data=data)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
            json_response = response.json()
            if json_response.get("status") == "error":
                logger.warning(f"API returned error status: {json_response}")
                raise self._map_error(response.status_code, json_response)
            logger.debug(f"Request successful: {response.status_code}")
            # Kite API often wraps successful responses in a 'data' field
            return json_response.get("data", {})

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {method} {url} - {e}")
            raise NetworkError(f"Request timed out: {e}", error_type="Timeout")
        except httpx.NetworkError as e:
            logger.error(f"Network error during request: {method} {url} - {e}")
            raise NetworkError(f"Network error: {e}", error_type="NetworkException")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} for {method} {url}. Response: {e.response.text}")
            try:
                response_data = e.response.json()
            except Exception:
                response_data = {"message": e.response.text, "error_type": "UnknownHttpError"}
            raise self._map_error(e.response.status_code, response_data)
        except KiteConnectError as e: # Re-raise specific mapped errors
             raise e
        except Exception as e:
            logger.exception(f"Unexpected error during request: {method} {url}")
            raise GeneralAPIError(f"An unexpected error occurred: {str(e)}", error_type="ClientException")

    async def place_order(self, params: PlaceOrderParams) -> Dict[str, Any]:
        """Place an order.

        Args:
            params: PlaceOrderParams object containing order details.

        Returns:
            Dictionary containing the order_id.

        Raises:
            KiteConnectError: If the API call fails.
        """
        endpoint = f"/orders/{params.variety}"
        # Convert Pydantic model to dict, removing None values
        data = params.dict(exclude={'variety'}, exclude_none=True)
        logger.info(f"Placing order to {endpoint} with data: {data}")
        return await self._request("POST", endpoint, data=data)

    async def modify_order(self, params: ModifyOrderParams) -> Dict[str, Any]:
        """Modify a pending order.

        Args:
            params: ModifyOrderParams object containing modification details.

        Returns:
            Dictionary containing the order_id.

        Raises:
            KiteConnectError: If the API call fails.
        """
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Convert Pydantic model to dict, removing None values and path params
        data = params.dict(exclude={'variety', 'order_id'}, exclude_none=True)
        logger.info(f"Modifying order {params.order_id} ({params.variety}) at {endpoint} with data: {data}")
        return await self._request("PUT", endpoint, data=data)

    async def close(self):
        """Close the underlying HTTPX client."""
        await self._client.aclose()
        logger.info("KiteConnectClient closed.")
