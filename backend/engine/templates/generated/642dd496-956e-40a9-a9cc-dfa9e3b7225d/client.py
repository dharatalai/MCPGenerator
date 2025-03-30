import os
import logging
from typing import Dict, Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from models import PlaceOrderParams, ModifyOrderParams

logger = logging.getLogger(__name__)

# --- Custom Exceptions ---
class KiteConnectError(Exception):
    """Base exception for Kite Connect client errors."""
    def __init__(self, message="Kite Connect API error", status_code: Optional[int] = None, details: Optional[Dict] = None):
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def __str__(self):
        return f"{super().__str__()} (Status: {self.status_code}, Details: {self.details})"

class AuthenticationError(KiteConnectError):
    """Error related to authentication (invalid API key or access token)."""
    pass

class NetworkError(KiteConnectError):
    """Error related to network connectivity or timeouts."""
    pass

class BadRequestError(KiteConnectError):
    """Error for general 4xx client errors (e.g., validation)."""
    pass

class OrderPlacementError(BadRequestError):
    """Specific error during order placement (e.g., insufficient funds, invalid params)."""
    pass

class OrderModificationError(BadRequestError):
    """Specific error during order modification (e.g., order not found, invalid state)."""
    pass

class RateLimitError(KiteConnectError):
    """Error when API rate limits are exceeded (HTTP 429)."""
    pass

class ServerError(KiteConnectError):
    """Error for 5xx server-side errors."""
    pass

# --- Kite Connect Client ---
class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect v3 API."""

    # Note: Kite Connect API has rate limits (e.g., 10 requests/second overall).
    # This client uses basic retry logic for transient errors but does not implement
    # sophisticated rate limiting. Consider using a library like 'limits' or
    # implementing token bucket/leaky bucket algorithm if needed.
    RETRY_ATTEMPTS = 3
    RETRY_WAIT_SECONDS = 2

    def __init__(self):
        self.api_key = os.getenv("KITE_API_KEY")
        self.access_token = os.getenv("KITE_ACCESS_TOKEN")
        self.base_url = os.getenv("KITE_API_BASE_URL", "https://api.kite.trade")

        if not self.api_key or not self.access_token:
            raise ValueError("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")

        self.headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            # Content-Type is set per request (form-data)
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0  # Set a reasonable timeout
        )

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_fixed(RETRY_WAIT_SECONDS),
        retry=retry_if_exception_type((NetworkError, RateLimitError, ServerError)),
        reraise=True, # Reraise the exception after retries are exhausted
        before_sleep=lambda retry_state: logger.warning(f"Retrying API call due to {retry_state.outcome.exception().__class__.__name__}, attempt {retry_state.attempt_number}...")
    )
    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite Connect API."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making {method} request to {url} with data: {data}")

        try:
            response = await self.client.request(method, endpoint, data=data)

            # Handle specific HTTP status codes
            if response.status_code == 400:
                error_details = self._parse_error_response(response)
                logger.error(f"Bad Request (400) for {method} {endpoint}: {error_details}")
                raise BadRequestError(message=error_details.get('message', 'Bad Request'), status_code=400, details=error_details)
            if response.status_code == 403:
                error_details = self._parse_error_response(response)
                logger.error(f"Authentication Error (403) for {method} {endpoint}: {error_details}")
                raise AuthenticationError(message=error_details.get('message', 'Forbidden/Authentication Error'), status_code=403, details=error_details)
            if response.status_code == 404:
                 error_details = self._parse_error_response(response)
                 logger.error(f"Not Found (404) for {method} {endpoint}: {error_details}")
                 raise BadRequestError(message=error_details.get('message', 'Resource Not Found'), status_code=404, details=error_details)
            if response.status_code == 429:
                logger.warning(f"Rate Limit Exceeded (429) for {method} {endpoint}. Retrying might be needed.")
                raise RateLimitError(message="Rate limit exceeded", status_code=429)
            if response.status_code >= 500:
                logger.error(f"Server Error ({response.status_code}) for {method} {endpoint}: {response.text}")
                raise ServerError(message=f"Kite API Server Error: {response.text}", status_code=response.status_code)

            # Raise for other 4xx errors not explicitly handled above
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx

            # Successful response (usually 200 OK)
            json_response = response.json()
            logger.debug(f"Received successful response ({response.status_code}) from {method} {endpoint}: {json_response}")
            return json_response

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out for {method} {endpoint}: {e}")
            raise NetworkError(f"Request timed out: {e}") from e
        except httpx.NetworkError as e:
            logger.error(f"Network error for {method} {endpoint}: {e}")
            raise NetworkError(f"Network error occurred: {e}") from e
        except httpx.HTTPStatusError as e:
            # This catches errors raised by response.raise_for_status() for unhandled 4xx/5xx
            error_details = self._parse_error_response(e.response)
            logger.error(f"HTTP Error ({e.response.status_code}) for {method} {endpoint}: {error_details}")
            # Map to a more specific error if possible based on status code
            if e.response.status_code >= 400 and e.response.status_code < 500:
                 raise BadRequestError(message=error_details.get('message', f'HTTP Client Error: {e.response.status_code}'), status_code=e.response.status_code, details=error_details) from e
            else:
                 raise ServerError(message=error_details.get('message', f'HTTP Server Error: {e.response.status_code}'), status_code=e.response.status_code, details=error_details) from e
        except Exception as e:
            logger.exception(f"Unexpected error during request to {method} {endpoint}: {e}")
            raise KiteConnectError(f"An unexpected error occurred: {e}") from e

    def _parse_error_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Attempts to parse error details from the Kite API response."""
        try:
            data = response.json()
            if isinstance(data, dict) and 'status' in data and data['status'] == 'error':
                return {
                    'message': data.get('message', 'Unknown error'),
                    'error_type': data.get('error_type', 'UnknownError')
                }
        except Exception:
            pass # Ignore if response is not valid JSON or doesn't match expected error format
        return {'message': response.text or f'HTTP Error {response.status_code}', 'error_type': 'UnknownHttpError'}

    def _prepare_payload(self, params: BaseModel, exclude_fields: set = None) -> Dict[str, Any]:
        """Converts Pydantic model to dictionary suitable for form data, excluding None values and specified fields."""
        if exclude_fields is None:
            exclude_fields = set()
        payload = params.dict(exclude_none=True, exclude=exclude_fields)
        # Convert relevant fields to string as expected by form encoding if necessary (httpx usually handles this)
        # For example, boolean might need 'true'/'false', but httpx handles common types.
        # Ensure numeric types are sent correctly.
        return payload

    async def place_order(self, params: PlaceOrderParams) -> Dict[str, Any]:
        """Place an order."""
        endpoint = f"/orders/{params.variety}"
        payload = self._prepare_payload(params, exclude_fields={'variety'})
        try:
            response_data = await self._request("POST", endpoint, data=payload)
            # Expecting {'status': 'success', 'data': {'order_id': '...'}}
            if response_data.get('status') == 'success' and 'data' in response_data and 'order_id' in response_data['data']:
                return response_data
            else:
                logger.error(f"place_order response format unexpected: {response_data}")
                raise OrderPlacementError(message="Order placement response format unexpected", details=response_data)
        except BadRequestError as e:
            # More specific error for placement issues
            raise OrderPlacementError(message=e.args[0], status_code=e.status_code, details=e.details) from e
        except KiteConnectError as e:
            # Catch other client errors
            raise e

    async def modify_order(self, params: ModifyOrderParams) -> Dict[str, Any]:
        """Modify a pending order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        payload = self._prepare_payload(params, exclude_fields={'variety', 'order_id'})
        try:
            response_data = await self._request("PUT", endpoint, data=payload)
            # Expecting {'status': 'success', 'data': {'order_id': '...'}}
            if response_data.get('status') == 'success' and 'data' in response_data and 'order_id' in response_data['data']:
                return response_data
            else:
                logger.error(f"modify_order response format unexpected: {response_data}")
                raise OrderModificationError(message="Order modification response format unexpected", details=response_data)
        except BadRequestError as e:
             # More specific error for modification issues (e.g., 400 or 404 if order_id invalid)
            raise OrderModificationError(message=e.args[0], status_code=e.status_code, details=e.details) from e
        except KiteConnectError as e:
            raise e
