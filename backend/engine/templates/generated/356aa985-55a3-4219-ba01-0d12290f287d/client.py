import httpx
import os
import logging
from typing import Dict, Any

from models import PlaceOrderParams, ModifyOrderParams, CancelOrderParams

logger = logging.getLogger(__name__)

# Custom Exception Hierarchy for Kite API Errors
class KiteApiException(Exception):
    """Base exception for Kite Connect API errors."""
    def __init__(self, message="Kite API error occurred", status_code=None, details=None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

    def __str__(self):
        return f"{self.__class__.__name__}: {self.message} (Status: {self.status_code}, Details: {self.details})"

class KiteInputException(KiteApiException):
    """Input validation errors (400 Bad Request)."""
    pass

class KiteTokenException(KiteApiException):
    """Authentication errors (403 Forbidden - Invalid Token)."""
    pass

class KitePermissionException(KiteApiException):
    """Permission errors (403 Forbidden - Other)."""
    pass

class KiteNetworkException(KiteApiException):
    """Network or connection errors."""
    pass

class KiteOrderException(KiteApiException):
    """Order placement/modification/cancellation errors (RMS, etc.). Often 400 or 500 status."""
    pass

class KiteRateLimitException(KiteApiException):
    """Rate limit exceeded (429 Too Many Requests)."""
    pass

class KiteGeneralException(KiteApiException):
    """Other unclassified API errors (e.g., 500 Internal Server Error)."""
    pass

class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect Orders API."""

    def __init__(self, timeout: float = 30.0):
        """Initializes the Kite Connect client.

        Args:
            timeout: Request timeout in seconds.

        Raises:
            ValueError: If required environment variables are not set.
        """
        self.api_key = os.getenv("KITE_API_KEY")
        self.access_token = os.getenv("KITE_ACCESS_TOKEN")
        self.base_url = os.getenv("KITE_API_BASE_URL", "https://api.kite.trade")

        if not self.api_key:
            raise ValueError("KITE_API_KEY environment variable not set.")
        if not self.access_token:
            raise ValueError("KITE_ACCESS_TOKEN environment variable not set.")

        self.headers = {
            "X-Kite-Version": "3",  # Specify Kite API version
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite uses form data
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=timeout
        )
        logger.info(f"KiteConnectClient initialized for base URL: {self.base_url}")

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous request to the Kite API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint path.
            data: Dictionary of form data for POST/PUT requests.

        Returns:
            The JSON response data as a dictionary.

        Raises:
            KiteApiException: If an API error occurs.
            KiteNetworkException: If a network error occurs.
        """
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making {method} request to {url} with data: {data}")

        try:
            response = await self.client.request(method, endpoint, data=data)

            logger.debug(f"Received response: Status={response.status_code}, Body={response.text[:500]}") # Log truncated body

            # Check for specific error status codes first
            if response.status_code == 400:
                error_data = self._parse_response(response)
                raise KiteInputException("Input validation error", response.status_code, error_data)
            elif response.status_code == 403:
                error_data = self._parse_response(response)
                # Differentiate between token and permission errors if possible from response
                if "token" in error_data.get("message", "").lower():
                     raise KiteTokenException("Authentication error (Invalid Token/Key)", response.status_code, error_data)
                else:
                     raise KitePermissionException("Permission denied", response.status_code, error_data)
            elif response.status_code == 429:
                raise KiteRateLimitException("Rate limit exceeded", response.status_code, self._parse_response(response))
            elif response.status_code == 500:
                 raise KiteGeneralException("Internal server error", response.status_code, self._parse_response(response))
            elif response.status_code >= 400: # Catch other 4xx/5xx errors
                error_data = self._parse_response(response)
                # Try to map to OrderException if context suggests it, otherwise GeneralException
                if "order" in endpoint: # Heuristic
                    raise KiteOrderException("Order operation failed", response.status_code, error_data)
                else:
                    raise KiteGeneralException("General API error", response.status_code, error_data)

            # Raise for status for any remaining >= 400 codes not explicitly handled
            response.raise_for_status()

            # Parse successful response
            json_response = self._parse_response(response)
            if json_response.get("status") == "error":
                # Handle cases where status is 200 but response indicates error
                message = json_response.get("message", "Unknown API error")
                logger.error(f"API returned 200 but error status: {message}")
                # Map based on message content if possible
                if "order" in message.lower() or "rms" in message.lower():
                    raise KiteOrderException(message, response.status_code, json_response)
                else:
                    raise KiteGeneralException(message, response.status_code, json_response)

            return json_response.get("data", {}) # Kite API wraps successful data in 'data'

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise KiteNetworkException(f"Request timed out: {e}")
        except httpx.RequestError as e:
            logger.error(f"HTTP request error: {e}")
            raise KiteNetworkException(f"HTTP request error: {e}")
        except KiteApiException: # Re-raise specific Kite exceptions
            raise
        except Exception as e:
            logger.exception(f"Unexpected error during API request: {e}")
            raise KiteGeneralException(f"An unexpected error occurred: {e}")

    def _parse_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Safely parses JSON response."""
        try:
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to parse JSON response (Status: {response.status_code}): {response.text}. Error: {e}")
            # Return a structured error if parsing fails but text might be useful
            return {"error": "Failed to parse JSON response", "raw_response": response.text}

    def _prepare_form_data(self, params: BaseModel) -> Dict[str, Any]:
        """Converts Pydantic model to a dictionary suitable for form data, excluding None values."""
        data = params.dict(exclude_unset=True, exclude_none=True)
        # Convert boolean/numeric types to string if required by API, but Kite usually handles them
        # Example: data = {k: str(v) for k, v in data.items()}
        return data

    async def place_order(self, params: PlaceOrderParams) -> Dict[str, str]:
        """Place an order.

        Args:
            params: Order placement parameters.

        Returns:
            Dictionary containing the 'order_id'.
        """
        endpoint = f"/orders/{params.variety}"
        # Exclude 'variety' from the form data as it's in the path
        form_data = self._prepare_form_data(params.copy(exclude={'variety'}))
        return await self._request("POST", endpoint, data=form_data)

    async def modify_order(self, params: ModifyOrderParams) -> Dict[str, str]:
        """Modify a pending order.

        Args:
            params: Order modification parameters.

        Returns:
            Dictionary containing the 'order_id'.
        """
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Exclude 'variety' and 'order_id' from the form data
        form_data = self._prepare_form_data(params.copy(exclude={'variety', 'order_id'}))
        return await self._request("PUT", endpoint, data=form_data)

    async def cancel_order(self, params: CancelOrderParams) -> Dict[str, str]:
        """Cancel a pending order.

        Args:
            params: Order cancellation parameters.

        Returns:
            Dictionary containing the 'order_id'.
        """
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Include parent_order_id in form data if present
        form_data = self._prepare_form_data(params.copy(exclude={'variety', 'order_id'}))
        # Note: DELETE requests typically don't have a body, but Kite uses form data here
        return await self._request("DELETE", endpoint, data=form_data)

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("KiteConnectClient closed.")
